import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

import {
  setup as baseSetup,
  user_trail_progress,
  user_trail_items_progress,
  user_trail_sections_progress,
} from './performance.test.js';

const WARMUP_DURATION = __ENV.PROGRESS_WARMUP_DURATION || '30s';
const STEP_DURATION = __ENV.PROGRESS_STEP_DURATION || '60s';
const STEP_PAUSE = __ENV.PROGRESS_STEP_PAUSE || '10s';
const MIN_RPS = Math.max(1, readNumberEnv('PROGRESS_MIN_RPS', 100));
const MAX_RPS = Math.max(MIN_RPS, readNumberEnv('PROGRESS_MAX_RPS', 1000));
const STEP_RPS = Math.max(1, readNumberEnv('PROGRESS_STEP_RPS', 100));
const FAILURE_TOLERANCE = Math.max(0, readNumberEnv('PROGRESS_FAILURE_TOLERANCE', 0.01));
const PRE_ALLOCATED_VUS = Math.max(1, readNumberEnv('PROGRESS_PRE_ALLOCATED_VUS', 80));
const MAX_VUS = Math.max(PRE_ALLOCATED_VUS, readNumberEnv('PROGRESS_MAX_VUS', PRE_ALLOCATED_VUS * 4));
const INSECURE_SKIP_TLS_VERIFY =
  (__ENV.INSECURE_SKIP_TLS_VERIFY || 'true').toLowerCase() !== 'false';

const progressRequestCounter = new Counter('progress_requests');
const progressFailureCounter = new Counter('progress_failures');

const PROGRESS_ENDPOINTS = [
  user_trail_progress,
  user_trail_items_progress,
  user_trail_sections_progress,
];

const warmupSeconds = durationToSeconds(WARMUP_DURATION);
const stepSeconds = durationToSeconds(STEP_DURATION);
const pauseSeconds = durationToSeconds(STEP_PAUSE);

const rates = [];
for (let rate = MIN_RPS; rate <= MAX_RPS; rate += STEP_RPS) {
  rates.push(rate);
}
if (rates.length === 0) {
  rates.push(MIN_RPS);
}

const PROBE_SCENARIOS = [];
const scenarios = {};
let offsetSeconds = 0;

scenarios.warmup = buildScenario({
  name: 'warmup',
  rate: Math.max(1, Math.round(MIN_RPS * 0.5)),
  duration: WARMUP_DURATION,
  startTime: offsetSeconds,
  tags: { stage: 'warmup', target_rps: String(Math.max(1, MIN_RPS / 2)) },
});
offsetSeconds += warmupSeconds;

for (const rate of rates) {
  const stageName = `progress_${rate}`;
  scenarios[stageName] = buildScenario({
    name: stageName,
    rate,
    duration: STEP_DURATION,
    startTime: offsetSeconds,
    tags: { stage: 'probe', target_rps: String(rate) },
  });
  PROBE_SCENARIOS.push({
    name: stageName,
    targetRps: rate,
    startTimeSeconds: offsetSeconds,
    durationSeconds: stepSeconds,
  });
  offsetSeconds += stepSeconds + pauseSeconds;
}

export const options = {
  insecureSkipTLSVerify: INSECURE_SKIP_TLS_VERIFY,
  summaryTrendStats: ['avg', 'min', 'max', 'p(90)', 'p(95)', 'p(99)'],
  scenarios,
  thresholds: {
    'http_req_failed{stage:probe}': [
      {
        threshold: `rate<${FAILURE_TOLERANCE}`,
        abortOnFail: true,
      },
    ],
    http_req_duration: [
      { threshold: 'p(95)<500', abortOnFail: false },
      { threshold: 'p(99)<750', abortOnFail: false },
    ],
  },
};

export function setup() {
  return baseSetup();
}

export function progress_iteration(data) {
  const index = typeof __ITER === 'number' && PROGRESS_ENDPOINTS.length
    ? __ITER % PROGRESS_ENDPOINTS.length
    : 0;
  const endpointExec = PROGRESS_ENDPOINTS[index];
  if (!endpointExec) {
    return;
  }

  const scenarioName = exec.scenario?.name || 'unknown';
  const targetTag = exec.scenario?.tags?.target_rps
    || (scenarioName.startsWith('progress_') ? scenarioName.slice('progress_'.length) : '');
  const counterTags = {
    scenario: scenarioName,
    target_rps: targetTag,
  };

  let response;
  try {
    response = endpointExec(data);
  } catch (error) {
    progressRequestCounter.add(1, counterTags);
    progressFailureCounter.add(1, counterTags);
    throw error;
  }

  if (!response) {
    return;
  }

  progressRequestCounter.add(1, counterTags);
  const failed = Boolean(response.error)
    || response.status >= 400
    || response.status === 0
    || Number.isNaN(Number(response.status));

  if (failed) {
    progressFailureCounter.add(1, counterTags);
  }
}

export function handleSummary(data) {
  const results = [];
  let highestPassing = null;

  for (const scenario of PROBE_SCENARIOS) {
    const requestMetric = findMetric(data.metrics, 'progress_requests', scenario.name);
    const failureMetric = findMetric(data.metrics, 'progress_failures', scenario.name);

    const requestCount = normalizeCount(requestMetric?.values?.count);
    const requestRate = scenario.durationSeconds > 0
      ? requestCount / scenario.durationSeconds
      : 0;
    const failedRequestsRaw = normalizeCount(failureMetric?.values?.count);
    const failedRequests = requestCount > 0
      ? Math.min(requestCount, failedRequestsRaw)
      : failedRequestsRaw;
    const failureRate = requestCount > 0 ? failedRequests / requestCount : 0;
    const passed = failureRate <= FAILURE_TOLERANCE
      && requestRate >= scenario.targetRps * 0.9;

    if (passed) {
      highestPassing = scenario.targetRps;
    }

    results.push({
      scenario: scenario.name,
      target_rps: scenario.targetRps,
      observed_rps: requestRate,
      requests: requestCount,
      failure_rate: failureRate,
      failed_requests: failedRequests,
      passed,
    });
  }

  const output = {
    min_target_rps: MIN_RPS,
    max_target_rps: MAX_RPS,
    step_rps: STEP_RPS,
    failure_tolerance: FAILURE_TOLERANCE,
    highest_passing_target: highestPassing,
    scenarios: results,
  };

  return {
    stdout: generateSummaryText(output),
    'performance/progress_probe_results.json': JSON.stringify(output, null, 2),
  };
}

function buildScenario({ name, rate, duration, startTime, tags }) {
  return {
    executor: 'constant-arrival-rate',
    exec: 'progress_iteration',
    rate,
    timeUnit: '1s',
    duration,
    preAllocatedVUs: PRE_ALLOCATED_VUS,
    maxVUs: MAX_VUS,
    startTime: secondsToDuration(startTime),
    gracefulStop: '10s',
    tags,
  };
}

function durationToSeconds(input) {
  if (typeof input === 'number' && Number.isFinite(input)) {
    return input;
  }
  if (typeof input !== 'string') {
    return 0;
  }
  const raw = input.trim();
  if (!raw) {
    return 0;
  }
  const match = raw.match(/^(\d+(?:\.\d+)?)(ms|s|m|h)$/i);
  if (!match) {
    const fallback = Number(raw);
    return Number.isFinite(fallback) ? fallback : 0;
  }
  const value = Number(match[1]);
  const unit = match[2].toLowerCase();
  switch (unit) {
    case 'ms':
      return value / 1000;
    case 's':
      return value;
    case 'm':
      return value * 60;
    case 'h':
      return value * 3600;
    default:
      return value;
  }
}

function secondsToDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '0s';
  }
  return `${seconds.toFixed(3).replace(/\.0+$/, '')}s`;
}

function readNumberEnv(key, fallback) {
  const raw = __ENV[key];
  if (raw === undefined || raw === null || raw === '') {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function findMetric(metrics, name, scenario) {
  if (!metrics) {
    return null;
  }
  const direct = `${name}{scenario:${scenario}}`;
  if (metrics[direct]) {
    return metrics[direct];
  }
  const baseMetric = metrics[name];
  if (baseMetric?.submetrics) {
    for (const [key, metric] of Object.entries(baseMetric.submetrics)) {
      const tags = extractMetricTags(key, name);
      if (tags.scenario === scenario) {
        return metric;
      }
    }
  }
  return null;
}

function extractMetricTags(key, metricName) {
  if (typeof key !== 'string') {
    return {};
  }
  let raw = key;
  if (metricName && raw.startsWith(metricName)) {
    const start = raw.indexOf('{');
    const end = raw.lastIndexOf('}');
    if (start >= 0 && end > start) {
      raw = raw.slice(start + 1, end);
    } else {
      raw = '';
    }
  }
  raw = raw.trim();
  if (!raw) {
    return {};
  }
  const tags = {};
  for (const part of raw.split(',')) {
    const segment = part.trim();
    if (!segment) {
      continue;
    }
    const separatorIndex = segment.indexOf(':');
    if (separatorIndex === -1) {
      continue;
    }
    const name = segment.slice(0, separatorIndex).trim();
    const value = segment.slice(separatorIndex + 1).trim().replace(/^"|"$/g, '');
    if (name) {
      tags[name] = value;
    }
  }
  return tags;
}

function normalizeCount(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    return 0;
  }
  return Math.round(value);
}

function generateSummaryText(output) {
  const lines = [];
  lines.push('========== Progress Probe ==========');
  lines.push(`Target range: ${output.min_target_rps}-${output.max_target_rps} RPS (step ${output.step_rps})`);
  lines.push(`Failure tolerance: ${(output.failure_tolerance * 100).toFixed(2)}%`);
  const highest = output.highest_passing_target;
  lines.push(`Highest passing target: ${highest === null ? 'none' : highest}`);
  lines.push('');
  lines.push('Per-target breakdown:');
  for (const result of output.scenarios) {
    lines.push(
      `- ${result.scenario} (target ${result.target_rps} RPS): observed ${result.observed_rps.toFixed(2)} RPS, `
      + `failures ${(result.failure_rate * 100).toFixed(2)}% [${result.passed ? 'PASS' : 'FAIL'}]`,
    );
  }
  lines.push('====================================');
  return lines.join('\n');
}
