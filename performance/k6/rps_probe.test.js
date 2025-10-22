import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

import {
  setup as baseSetup,
  trails_showcase,
  trails_list,
  trails_detail,
  trails_sections,
  trails_section_items,
  trails_sections_with_items,
  trails_included_items,
  trails_requirements,
  trails_audience,
  trails_learn,
  trail_item_detail,
  user_trail_enroll,
  user_trail_progress,
  user_trail_items_progress,
  user_trail_sections_progress,
  me_profile,
  trail_item_progress,
  trail_form_submission,
} from './performance.test.js';

const MIN_RPS = Math.max(1, readNumberEnv('MIN_PROBE_RPS', 10));
const MAX_RPS = Math.max(MIN_RPS, readNumberEnv('MAX_PROBE_RPS', 100));
const STEP_RPS = Math.max(1, readNumberEnv('PROBE_STEP_RPS', 10));
const WARMUP_DURATION = __ENV.PROBE_WARMUP_DURATION || '30s';
const STEP_DURATION = __ENV.PROBE_STEP_DURATION || '30s';
const STEP_PAUSE = __ENV.PROBE_STEP_PAUSE || '5s';
const FAILURE_TOLERANCE = Math.max(0, readNumberEnv('PROBE_FAILURE_TOLERANCE', 0.01));
const PRE_ALLOCATED_VUS = Math.max(1, readNumberEnv('PRE_ALLOCATED_VUS', 50));
const MAX_VUS = Math.max(
  PRE_ALLOCATED_VUS,
  readNumberEnv('MAX_VUS', Math.max(PRE_ALLOCATED_VUS * 4, PRE_ALLOCATED_VUS + 20)),
);
const INSECURE_SKIP_TLS_VERIFY = (__ENV.INSECURE_SKIP_TLS_VERIFY || 'true').toLowerCase() !== 'false';
const ENABLE_WRITE_SCENARIOS =
  (__ENV.ENABLE_WRITE_SCENARIOS || 'true').toLowerCase() !== 'false';

const probeRequestCounter = new Counter('probe_requests');
const probeFailureCounter = new Counter('probe_failures');

const BASE_PROBE_ENDPOINTS = [
  trails_showcase,
  trails_list,
  trails_detail,
  trails_sections,
  trails_section_items,
  trails_sections_with_items,
  trails_included_items,
  trails_requirements,
  trails_audience,
  trails_learn,
  trail_item_detail,
  user_trail_progress,
  user_trail_items_progress,
  user_trail_sections_progress,
  me_profile,
];

const WRITE_PROBE_ENDPOINTS = ENABLE_WRITE_SCENARIOS
  ? [user_trail_enroll, trail_item_progress, trail_form_submission]
  : [];

const PROBE_ENDPOINTS = [...BASE_PROBE_ENDPOINTS, ...WRITE_PROBE_ENDPOINTS];

const rates = [];
for (let rate = MIN_RPS; rate <= MAX_RPS; rate += STEP_RPS) {
  rates.push(rate);
}

if (rates.length === 0) {
  rates.push(MIN_RPS);
}

const warmupSeconds = durationToSeconds(WARMUP_DURATION);
const stepSeconds = durationToSeconds(STEP_DURATION);
const pauseSeconds = durationToSeconds(STEP_PAUSE);

const PROBE_SCENARIOS = [];
const scenarios = {};
let offsetSeconds = 0;

scenarios.warmup = {
  executor: 'constant-arrival-rate',
  exec: 'probe_iteration',
  rate: Math.max(1, MIN_RPS),
  timeUnit: '1s',
  duration: WARMUP_DURATION,
  preAllocatedVUs: PRE_ALLOCATED_VUS,
  maxVUs: MAX_VUS,
  startTime: secondsToDuration(offsetSeconds),
  gracefulStop: '10s',
  tags: { stage: 'warmup', target_rps: String(Math.max(1, MIN_RPS)) },
};

offsetSeconds += warmupSeconds;

for (const rate of rates) {
  const name = `probe_${rate}`;
  scenarios[name] = {
    executor: 'constant-arrival-rate',
    exec: 'probe_iteration',
    rate,
    timeUnit: '1s',
    duration: STEP_DURATION,
    preAllocatedVUs: PRE_ALLOCATED_VUS,
    maxVUs: MAX_VUS,
    startTime: secondsToDuration(offsetSeconds),
    gracefulStop: '10s',
    tags: { stage: 'probe', target_rps: String(rate) },
  };

  PROBE_SCENARIOS.push({
    name,
    targetRps: rate,
    startTimeSeconds: offsetSeconds,
    durationSeconds: stepSeconds,
  });

  offsetSeconds += stepSeconds + pauseSeconds;
}

export const options = {
  insecureSkipTLSVerify: INSECURE_SKIP_TLS_VERIFY,
  scenarios,
  summaryTrendStats: ['avg', 'min', 'max', 'p(90)', 'p(95)', 'p(99)'],
  thresholds: {
    'http_req_failed{stage:probe}': [
      {
        threshold: `rate<${FAILURE_TOLERANCE}`,
        abortOnFail: true,
      },
    ],
    http_req_duration: [
      { threshold: 'p(95)<1000', abortOnFail: false },
      { threshold: 'p(99)<2000', abortOnFail: false },
    ],
  },
};

export function setup() {
  return baseSetup();
}

export function probe_iteration(data) {
  const index = typeof __ITER === 'number' && PROBE_ENDPOINTS.length
    ? __ITER % PROBE_ENDPOINTS.length
    : 0;
  const endpointExec = PROBE_ENDPOINTS[index];
  if (!endpointExec) {
    return;
  }

  const scenarioName = exec.scenario?.name || 'unknown';
  const targetTag = exec.scenario?.tags?.target_rps
    || (scenarioName.startsWith('probe_') ? scenarioName.slice('probe_'.length) : '');
  const counterTags = {
    scenario: scenarioName,
    target_rps: targetTag,
  };

  let response;
  try {
    response = endpointExec(data);
  } catch (error) {
    probeRequestCounter.add(1, counterTags);
    probeFailureCounter.add(1, counterTags);
    throw error;
  }

  if (!response) {
    return;
  }

  probeRequestCounter.add(1, counterTags);

  const failed = Boolean(response.error)
    || response.status >= 400
    || response.status === 0
    || Number.isNaN(Number(response.status));

  if (failed) {
    probeFailureCounter.add(1, counterTags);
  }
}

export function handleSummary(data) {
  const summaryLines = [];
  summaryLines.push('========== RPS Probe Summary =========');
  summaryLines.push(`Target range: ${MIN_RPS}-${MAX_RPS} RPS (step ${STEP_RPS})`);
  summaryLines.push(`Failure tolerance: ${(FAILURE_TOLERANCE * 100).toFixed(2)}%`);

  const results = [];
  let highestPassing = null;

  for (const scenario of PROBE_SCENARIOS) {
    const requestMetric = findMetric(data.metrics, 'probe_requests', scenario.name);
    const failureMetric = findMetric(data.metrics, 'probe_failures', scenario.name);

    const requestCount = normalizeCount(requestMetric?.values?.count);
    const requestRate = scenario.durationSeconds > 0
      ? requestCount / scenario.durationSeconds
      : 0;

    const failedRequestsRaw = normalizeCount(failureMetric?.values?.count);
    const failedRequests = requestCount > 0
      ? Math.min(requestCount, failedRequestsRaw)
      : failedRequestsRaw;
    const failureRate = requestCount > 0
      ? Math.min(1, Math.max(0, failedRequests / requestCount))
      : 0;

    const passed = requestCount > 0 && failureRate <= FAILURE_TOLERANCE;

    if (passed) {
      highestPassing = scenario;
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

  if (highestPassing) {
    summaryLines.push(`Highest passing target: ${highestPassing.targetRps} RPS`);
  } else {
    summaryLines.push('Highest passing target: none (all targets failed)');
  }

  summaryLines.push('');
  summaryLines.push('Per-target breakdown:');
  for (const result of results) {
    const status = result.passed ? 'PASS' : 'FAIL';
    summaryLines.push(
      `- ${result.scenario} (target ${result.target_rps} RPS): `
        + `observed ${result.observed_rps.toFixed(2)} RPS, `
        + `failures ${(result.failure_rate * 100).toFixed(2)}% [${status}]`,
    );
  }
  summaryLines.push('=======================================');

  const stdout = `${summaryLines.join('\n')}\n`;
  const json = {
    min_target_rps: MIN_RPS,
    max_target_rps: MAX_RPS,
    step_rps: STEP_RPS,
    failure_tolerance: FAILURE_TOLERANCE,
    highest_passing_target: highestPassing ? highestPassing.targetRps : null,
    scenarios: results,
    total_duration_seconds: data.state?.testRunDurationMs
      ? data.state.testRunDurationMs / 1000
      : null,
  };

  return {
    stdout,
    'performance/rps_results.json': JSON.stringify(json, null, 2),
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

function findMetric(metrics, name, scenario) {
  if (!metrics) {
    return null;
  }

  const baseMetric = metrics[name];
  if (!scenario) {
    return baseMetric || null;
  }

  const direct = `${name}{scenario:${scenario}}`;
  if (metrics[direct]) {
    return metrics[direct];
  }

  const taggedMetric = findTaggedMetric(metrics, name, scenario);
  if (taggedMetric) {
    return taggedMetric;
  }

  if (baseMetric?.submetrics) {
    const submetric = findTaggedMetric(baseMetric.submetrics, null, scenario);
    if (submetric) {
      return submetric;
    }
  }

  return null;
}

function readNumberEnv(key, fallback) {
  const raw = __ENV[key];
  if (raw === undefined || raw === null || raw === '') {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function findTaggedMetric(collection, metricName, scenario) {
  if (!collection) {
    return null;
  }

  for (const [key, metric] of Object.entries(collection)) {
    const tags = extractMetricTags(key, metricName);
    if (tags.scenario === scenario) {
      return metric;
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

  if (raw.startsWith('{') && raw.endsWith('}')) {
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed;
      }
    } catch (error) {
      raw = raw.slice(1, -1);
    }
  }

  const tags = {};
  for (const part of raw.split(',')) {
    const segment = part.trim();
    if (!segment) {
      continue;
    }

    let separatorIndex = segment.indexOf(':');
    if (separatorIndex === -1) {
      separatorIndex = segment.indexOf('=');
    }
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
  if (value === 0) {
    return 0;
  }
  return Math.round(value);
}
