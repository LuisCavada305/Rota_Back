import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

import {
  setup as baseSetup,
  trail_item_progress,
} from './performance.test.js';

const TEST_DURATION = __ENV.PROGRESS_WRITE_DURATION || '2m';
const WARMUP_DURATION = __ENV.PROGRESS_WRITE_WARMUP || '30s';
const COOLDOWN_DURATION = __ENV.PROGRESS_WRITE_COOLDOWN || '30s';
const TARGET_RPS = Math.max(1, readNumberEnv('PROGRESS_WRITE_RPS', 500));
const FAILURE_TOLERANCE = Math.max(0, readNumberEnv('PROGRESS_WRITE_FAILURE_TOLERANCE', 0.02));
const PRE_ALLOCATED_VUS = Math.max(1, readNumberEnv('PROGRESS_WRITE_PRE_ALLOCATED_VUS', 100));
const MAX_VUS = Math.max(
  PRE_ALLOCATED_VUS,
  readNumberEnv('PROGRESS_WRITE_MAX_VUS', PRE_ALLOCATED_VUS * 4),
);
const INSECURE_SKIP_TLS_VERIFY =
  (__ENV.INSECURE_SKIP_TLS_VERIFY || 'true').toLowerCase() !== 'false';

const requestCounter = new Counter('progress_write_requests');
const failureCounter = new Counter('progress_write_failures');

const stages = buildStages();

export const options = {
  insecureSkipTLSVerify: INSECURE_SKIP_TLS_VERIFY,
  summaryTrendStats: ['avg', 'min', 'max', 'p(90)', 'p(95)', 'p(99)'],
  scenarios: {
    progress_write: {
      executor: 'ramping-arrival-rate',
      exec: 'progress_write_iteration',
      startRate: Math.max(1, Math.round(TARGET_RPS * 0.25)),
      timeUnit: '1s',
      stages,
      preAllocatedVUs: PRE_ALLOCATED_VUS,
      maxVUs: MAX_VUS,
      gracefulStop: '20s',
      tags: {
        stage: 'write',
        target_rps: String(TARGET_RPS),
      },
    },
  },
  thresholds: {
    'http_req_failed{stage:write}': [
      {
        threshold: `rate<${FAILURE_TOLERANCE}`,
        abortOnFail: true,
      },
    ],
    http_req_duration: [
      { threshold: 'p(95)<750', abortOnFail: false },
      { threshold: 'p(99)<1500', abortOnFail: false },
    ],
    progress_write_failures: [
      { threshold: 'count==0', abortOnFail: false },
    ],
  },
};

function buildStages() {
  const warmupSeconds = durationToSeconds(WARMUP_DURATION);
  const cooldownSeconds = durationToSeconds(COOLDOWN_DURATION);
  const stagesList = [];

  if (warmupSeconds > 0) {
    stagesList.push({
      duration: WARMUP_DURATION,
      target: Math.max(1, Math.round(TARGET_RPS * 0.5)),
    });
  }

  stagesList.push({ duration: TEST_DURATION, target: TARGET_RPS });

  if (cooldownSeconds > 0) {
    stagesList.push({
      duration: COOLDOWN_DURATION,
      target: Math.max(1, Math.round(TARGET_RPS * 0.25)),
    });
  }

  stagesList.push({ duration: '10s', target: 0 });
  return stagesList;
}

export function setup() {
  return baseSetup();
}

export function progress_write_iteration(data) {
  const scenarioName = exec.scenario?.name || 'progress_write';
  const targetTag = exec.scenario?.tags?.target_rps || String(TARGET_RPS);
  const tags = {
    scenario: scenarioName,
    target_rps: targetTag,
  };

  let response;
  try {
    response = trail_item_progress(data);
  } catch (error) {
    requestCounter.add(1, tags);
    failureCounter.add(1, tags);
    throw error;
  }

  if (!response) {
    return;
  }

  requestCounter.add(1, tags);

  const failed = Boolean(response.error)
    || response.status >= 400
    || response.status === 0
    || Number.isNaN(Number(response.status));

  if (failed) {
    const statusTag = String(
      response && response.status !== undefined ? response.status : 'error',
    );
    failureCounter.add(1, { ...tags, status: statusTag });
  }
}

export function handleSummary(data) {
  const scenarioName = 'progress_write';
  const requestMetric = findMetric(data.metrics, 'progress_write_requests', scenarioName);
  const failureMetric = findMetric(data.metrics, 'progress_write_failures', scenarioName);

  const totalRequests = resolveCount(data.metrics, 'progress_write_requests', requestMetric);
  const totalFailures = resolveCount(data.metrics, 'progress_write_failures', failureMetric);
  const failureRate = totalRequests > 0 ? totalFailures / totalRequests : 0;

  const warmupSeconds = durationToSeconds(WARMUP_DURATION);
  const mainSeconds = durationToSeconds(TEST_DURATION);
  const cooldownSeconds = durationToSeconds(COOLDOWN_DURATION);
  const totalSeconds = warmupSeconds + mainSeconds + cooldownSeconds;

  const observedRps = totalSeconds > 0 ? totalRequests / totalSeconds : 0;
  const plateauSeconds = durationToSeconds(TEST_DURATION);
  const observedPlateauRps = plateauSeconds > 0 ? totalRequests / plateauSeconds : 0;

  const output = {
    target_rps: TARGET_RPS,
    warmup_duration: WARMUP_DURATION,
    test_duration: TEST_DURATION,
    cooldown_duration: COOLDOWN_DURATION,
    failure_tolerance: FAILURE_TOLERANCE,
    observed_rps: observedRps,
    observed_rps_plateau: observedPlateauRps,
    total_requests: totalRequests,
    total_failures: totalFailures,
    failure_rate: failureRate,
    passed: failureRate <= FAILURE_TOLERANCE,
  };

  return {
    stdout: generateSummaryText(output),
    'performance/progress_write_results.json': JSON.stringify(output, null, 2),
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
  const raw = extractRawTagBlock(key, metricName);
  if (!raw) {
    return {};
  }
  const jsonCandidate = raw.replace(/([a-zA-Z0-9_]+):/g, '"$1":');
  try {
    return JSON.parse(`{${jsonCandidate}}`);
  } catch (error) {
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
}

function normalizeCount(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    return 0;
  }
  return Math.round(value);
}

function resolveCount(metrics, metricName, metricWithTags) {
  if (metricWithTags?.values?.count !== undefined) {
    return normalizeCount(metricWithTags.values.count);
  }
  const baseMetric = metrics?.[metricName];
  if (baseMetric?.values?.count !== undefined) {
    return normalizeCount(baseMetric.values.count);
  }
  return 0;
}

function extractRawTagBlock(key, metricName) {
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
  return raw.trim();
}

function generateSummaryText(output) {
  const lines = [];
  lines.push('========== Progress Write ==========');
  lines.push(`Target RPS: ${output.target_rps}`);
  lines.push(
    `Warmup: ${output.warmup_duration}, Test: ${output.test_duration}, Cooldown: ${output.cooldown_duration}`,
  );
  lines.push(`Observed RPS: ${output.observed_rps.toFixed(2)}`);
  lines.push(`Plateau RPS (test window): ${output.observed_rps_plateau.toFixed(2)}`);
  lines.push(
    `Failures: ${output.total_failures}/${output.total_requests} `
      + `(${(output.failure_rate * 100).toFixed(2)}%)`,
  );
  lines.push(
    `Status: ${output.passed ? 'PASS' : 'FAIL (above tolerance)'} `
      + `(tolerance ${(output.failure_tolerance * 100).toFixed(2)}%)`,
  );
  lines.push('====================================');
  return lines.join('\n');
}
