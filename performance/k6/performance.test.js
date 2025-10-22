import http from 'k6/http';
import { check, fail, sleep } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'https://127.0.0.1:8001';
const AUTH_EMAIL = __ENV.AUTH_EMAIL || '';
const AUTH_PASSWORD = __ENV.AUTH_PASSWORD || 'PerfTest@123';
const AUTH_USERNAME = __ENV.AUTH_USERNAME || '';
const DEFAULT_RATE = Number(__ENV.TARGET_RPS || 5);
const DEFAULT_DURATION = __ENV.TEST_DURATION || '2m';
const WARMUP_DURATION = __ENV.WARMUP_DURATION || '30s';
const COOLDOWN_DURATION = __ENV.COOLDOWN_DURATION || '30s';
const FINAL_STAGE_DURATION = '15s';
const DEFAULT_VUS = Number(__ENV.PRE_ALLOCATED_VUS || 20);
const MAX_VUS = Number(__ENV.MAX_VUS || Math.max(DEFAULT_VUS * 4, DEFAULT_VUS + 10));
const WRITE_RATE = Number(
  __ENV.WRITE_RPS || Math.max(1, Math.round(DEFAULT_RATE / 4)),
);
const ENABLE_WRITE_SCENARIOS = (__ENV.ENABLE_WRITE_SCENARIOS || 'true').toLowerCase() !== 'false';
const ENABLE_RATE_LIMIT_SCENARIOS =
  (__ENV.ENABLE_RATE_LIMIT_SCENARIOS || 'false').toLowerCase() === 'true';
const SESSION_COOKIE_NAME = __ENV.SESSION_COOKIE_NAME || 'rota_session';
const CSRF_COOKIE_NAME = __ENV.CSRF_COOKIE_NAME || 'rota_csrftoken';
const SESSION_COOKIE_CANDIDATES = buildCookieCandidates(
  SESSION_COOKIE_NAME,
  __ENV.SESSION_COOKIE_ALIASES,
  ['rota_session', 'sessionid', 'session'],
);
const CSRF_COOKIE_CANDIDATES = buildCookieCandidates(
  CSRF_COOKIE_NAME,
  __ENV.CSRF_COOKIE_ALIASES,
  ['rota_csrftoken', 'rota_csrf', 'csrftoken', 'csrf_token', 'xsrf-token', 'xsrftoken'],
);
const INSECURE_SKIP_TLS_VERIFY =
  (__ENV.INSECURE_SKIP_TLS_VERIFY || 'true').toLowerCase() !== 'false';
const RATE_LIMIT_MAX_ATTEMPTS = Number(__ENV.AUTH_RATE_LIMIT_MAX_ATTEMPTS || 10);
const RATE_LIMIT_WINDOW_SECONDS = Number(__ENV.AUTH_RATE_LIMIT_WINDOW_SECONDS || 60);
const LOGIN_USER_POOL = Number(__ENV.LOGIN_USER_POOL || 0);
const WARMUP_SECONDS = durationToSeconds(WARMUP_DURATION);
const DEFAULT_SECONDS = durationToSeconds(DEFAULT_DURATION);
const COOLDOWN_SECONDS = durationToSeconds(COOLDOWN_DURATION);
const FINAL_STAGE_SECONDS = durationToSeconds(FINAL_STAGE_DURATION);

function buildStages(targetRate) {
  const warmupTarget = Math.max(1, Math.round(targetRate * 0.5));
  const coolTarget = Math.max(1, Math.round(targetRate * 0.25));
  return [
    { duration: WARMUP_DURATION, target: warmupTarget },
    { duration: DEFAULT_DURATION, target: targetRate },
    { duration: COOLDOWN_DURATION, target: coolTarget },
    { duration: FINAL_STAGE_DURATION, target: 0 },
  ];
}

const endpointLatency = new Trend('endpoint_duration_ms', true);
const responseBodySize = new Trend('response_body_bytes', true);
const endpointFailures = new Counter('endpoint_failures');
const skipNotices = {};

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

function buildCookieCandidates(primaryName, envList, fallback = []) {
  const parts = [];
  if (primaryName) {
    parts.push(primaryName);
  }
  if (envList) {
    parts.push(
      ...String(envList)
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    );
  }
  parts.push(...fallback);
  const seen = new Set();
  const result = [];
  for (const name of parts) {
    const lower = name.toLowerCase();
    if (seen.has(lower)) {
      continue;
    }
    seen.add(lower);
    result.push(name);
  }
  return result;
}

function scenario(definitionOverrides = {}) {
  const targetRate = definitionOverrides.targetRate || DEFAULT_RATE;
  const tags = definitionOverrides.tags || { traffic: 'read' };
  const stages = definitionOverrides.stages || buildStages(targetRate);

  const baseConfig = {
    executor: 'ramping-arrival-rate',
    startRate: Math.max(1, Math.round(targetRate * 0.25)),
    timeUnit: '1s',
    stages,
    preAllocatedVUs: DEFAULT_VUS,
    maxVUs: MAX_VUS,
    gracefulStop: '30s',
    tags,
  };

  const overrides = { ...definitionOverrides };
  delete overrides.targetRate;
  delete overrides.tags;
  delete overrides.stages;

  return { ...baseConfig, ...overrides };
}

function nextLoginCredential(ctx) {
  if (Array.isArray(ctx.loginPool) && ctx.loginPool.length > 0) {
    const pool = ctx.loginPool;
    const iter = typeof __ITER === 'number' ? __ITER : 0;
    const vu = typeof __VU === 'number' ? __VU : 0;
    const index = (iter + vu) % pool.length;
    return pool[index];
  }
  return ctx.credentials;
}

const endpointDefinitions = {
  trails_showcase: {
    name: 'GET /trails/showcase',
    method: 'GET',
    path: () => '/trails/showcase',
  },
  trails_list: {
    name: 'GET /trails',
    method: 'GET',
    path: () => '/trails/',
  },
  trails_detail: {
    name: 'GET /trails/:id',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}`,
    requires: ['dataset.trailId'],
  },
  trails_sections: {
    name: 'GET /trails/:id/sections',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/sections`,
    requires: ['dataset.trailId'],
  },
  trails_section_items: {
    name: 'GET /trails/:id/sections/:sectionId/items',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/sections/${ctx.dataset.sectionId}/items`,
    requires: ['dataset.trailId', 'dataset.sectionId'],
  },
  trails_sections_with_items: {
    name: 'GET /trails/:id/sections-with-items',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/sections-with-items`,
    requires: ['dataset.trailId'],
  },
  trails_included_items: {
    name: 'GET /trails/:id/included-items',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/included-items`,
    requires: ['dataset.trailId'],
  },
  trails_requirements: {
    name: 'GET /trails/:id/requirements',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/requirements`,
    requires: ['dataset.trailId'],
  },
  trails_audience: {
    name: 'GET /trails/:id/audience',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/audience`,
    requires: ['dataset.trailId'],
  },
  trails_learn: {
    name: 'GET /trails/:id/learn',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/learn`,
    requires: ['dataset.trailId'],
  },
  trail_item_detail: {
    name: 'GET /trails/:id/items/:itemId',
    method: 'GET',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/items/${ctx.dataset.itemId}`,
    authRequired: true,
    requires: ['dataset.trailId', 'dataset.itemId'],
  },
  auth_login: {
    name: 'POST /auth/login',
    method: 'POST',
    path: () => '/auth/login',
    testPhase: 'auth',
    headers: { 'Content-Type': 'application/json' },
    acceptableStatus: [200, 429],
    markExpected: true,
    body: (ctx) => {
      const creds = nextLoginCredential(ctx);
      return JSON.stringify({
        email: creds.email,
        password: creds.password,
        remember: true,
      });
    },
  },
  user_trail_enroll: {
    name: 'POST /user-trails/:trailId/enroll',
    method: 'POST',
    path: (ctx) => `/user-trails/${ctx.dataset.trailId}/enroll`,
    requires: ['dataset.trailId'],
    authRequired: true,
    requireCsrf: true,
    testPhase: 'write',
  },
  user_trail_progress: {
    name: 'GET /user-trails/:trailId/progress',
    method: 'GET',
    path: (ctx) => `/user-trails/${ctx.dataset.trailId}/progress`,
    requires: ['dataset.trailId'],
    authRequired: true,
  },
  user_trail_items_progress: {
    name: 'GET /user-trails/:trailId/items-progress',
    method: 'GET',
    path: (ctx) => `/user-trails/${ctx.dataset.trailId}/items-progress`,
    requires: ['dataset.trailId'],
    authRequired: true,
  },
  user_trail_sections_progress: {
    name: 'GET /user-trails/:trailId/sections-progress',
    method: 'GET',
    path: (ctx) => `/user-trails/${ctx.dataset.trailId}/sections-progress`,
    requires: ['dataset.trailId'],
    authRequired: true,
  },
  me_profile: {
    name: 'GET /me',
    method: 'GET',
    path: () => '/me',
    authRequired: true,
  },
  trail_item_progress: {
    name: 'PUT /trails/:id/items/:itemId/progress',
    method: 'PUT',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/items/${ctx.dataset.itemId}/progress`,
    requires: ['dataset.trailId', 'dataset.itemId'],
    authRequired: true,
    requireCsrf: true,
    testPhase: 'write',
    body: (ctx) => {
      const payload = {
        status: 'IN_PROGRESS',
        progress_value: 30,
      };
      if (ctx.dataset.itemDurationSeconds) {
        payload.progress_value = Math.min(
          Math.max(10, Math.floor(ctx.dataset.itemDurationSeconds * 0.3)),
          ctx.dataset.itemDurationSeconds,
        );
      }
      return JSON.stringify(payload);
    },
  },
  trail_form_submission: {
    name: 'POST /trails/:id/items/:itemId/form-submissions',
    method: 'POST',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/items/${ctx.dataset.formItemId}/form-submissions`,
    requires: ['dataset.trailId', 'dataset.formItemId', 'dataset.formQuestions'],
    authRequired: true,
    requireCsrf: true,
    testPhase: 'write',
    body: (ctx) => JSON.stringify({
      duration_seconds: 30,
      answers: ctx.dataset.formQuestions.map((question) => ({
        question_id: question.id,
        selected_option_id: question.firstOptionId,
        answer_text: question.firstOptionId ? null : 'Benchmark answer',
      })),
    }),
  },
};

const thresholdConfig = {
  'http_req_failed{phase:main}': [{ threshold: 'rate<0.01', abortOnFail: true }],
  'http_req_failed{phase:write}': [{ threshold: 'rate<=1', abortOnFail: false }],
  http_req_duration: [
    { threshold: 'p(95)<500', abortOnFail: false },
    { threshold: 'p(99)<1000', abortOnFail: false },
  ],
  endpoint_duration_ms: [{ threshold: 'p(95)<450' }],
};

if (ENABLE_RATE_LIMIT_SCENARIOS) {
  thresholdConfig['http_req_failed{phase:auth}'] = [{ threshold: 'rate<=1', abortOnFail: false }];
}

const scenarios = {
  trails_showcase: scenario({ exec: 'trails_showcase', tags: { traffic: 'read' } }),
  trails_list: scenario({ exec: 'trails_list', tags: { traffic: 'read' } }),
  trails_detail: scenario({ exec: 'trails_detail', tags: { traffic: 'read' } }),
  trails_sections: scenario({ exec: 'trails_sections', tags: { traffic: 'read' } }),
  trails_section_items: scenario({
    exec: 'trails_section_items',
    tags: { traffic: 'read' },
  }),
  trails_sections_with_items: scenario({
    exec: 'trails_sections_with_items',
    tags: { traffic: 'read' },
  }),
  trails_included_items: scenario({
    exec: 'trails_included_items',
    tags: { traffic: 'read' },
  }),
  trails_requirements: scenario({
    exec: 'trails_requirements',
    tags: { traffic: 'read' },
  }),
  trails_audience: scenario({
    exec: 'trails_audience',
    tags: { traffic: 'read' },
  }),
  trails_learn: scenario({ exec: 'trails_learn', tags: { traffic: 'read' } }),
  trail_item_detail: scenario({
    exec: 'trail_item_detail',
    tags: { traffic: 'read' },
  }),
  user_trail_enroll: scenario({
    exec: 'user_trail_enroll',
    targetRate: WRITE_RATE,
    gracefulStop: '0s',
    tags: { traffic: 'write' },
  }),
  user_trail_progress: scenario({
    exec: 'user_trail_progress',
    tags: { traffic: 'read' },
  }),
  user_trail_items_progress: scenario({
    exec: 'user_trail_items_progress',
    tags: { traffic: 'read' },
  }),
  user_trail_sections_progress: scenario({
    exec: 'user_trail_sections_progress',
    tags: { traffic: 'read' },
  }),
  me_profile: scenario({ exec: 'me_profile', tags: { traffic: 'read' } }),
};

if (ENABLE_RATE_LIMIT_SCENARIOS) {
  scenarios.auth_login = scenario({
    exec: 'auth_login',
    targetRate: WRITE_RATE,
    tags: { traffic: 'auth' },
  });
}

if (ENABLE_WRITE_SCENARIOS) {
  scenarios.trail_item_progress = scenario({
    exec: 'trail_item_progress',
    targetRate: WRITE_RATE,
    tags: { traffic: 'write' },
  });
  scenarios.trail_form_submission = scenario({
    exec: 'trail_form_submission',
    targetRate: WRITE_RATE,
    tags: { traffic: 'write' },
  });
}

export const options = {
  insecureSkipTLSVerify: INSECURE_SKIP_TLS_VERIFY,
  thresholds: thresholdConfig,
  summaryTrendStats: ['avg', 'min', 'max', 'p(90)', 'p(95)', 'p(99)'],
  scenarios,
};

function resolvePath(obj, path) {
  return path.split('.').reduce((acc, key) => {
    if (acc === undefined || acc === null) {
      return undefined;
    }
    return acc[key];
  }, obj);
}

function noteSkip(key, reason) {
  if (skipNotices[key]) {
    return;
  }
  skipNotices[key] = true;
  console.warn(`Skipping ${endpointDefinitions[key].name}: ${reason}`);
}

function cookieFromResponse(res, primaryName, candidates = [], predicate = null) {
  const cookies = res.cookies || {};
  const searchOrder = [];
  if (primaryName) {
    searchOrder.push(primaryName);
  }
  if (Array.isArray(candidates)) {
    searchOrder.push(...candidates);
  }

  const seen = new Set();
  for (const name of searchOrder) {
    if (!name) {
      continue;
    }
    const lower = name.toLowerCase();
    if (seen.has(lower)) {
      continue;
    }
    seen.add(lower);
    const direct = cookies[name];
    if (direct && direct.length > 0) {
      return { name, value: direct[direct.length - 1].value };
    }
    const matchedKey = Object.keys(cookies).find((key) => key.toLowerCase() === lower);
    if (matchedKey) {
      const values = cookies[matchedKey];
      if (values && values.length > 0) {
        return { name: matchedKey, value: values[values.length - 1].value };
      }
    }
  }

  if (typeof predicate === 'function') {
    for (const [name, values] of Object.entries(cookies)) {
      if (!values || values.length === 0) {
        continue;
      }
      if (predicate(name)) {
        return { name, value: values[values.length - 1].value };
      }
    }
  }

  return null;
}

function headerFromResponse(headers, names = []) {
  if (!headers) {
    return '';
  }
  const normalized = {};
  for (const [key, value] of Object.entries(headers)) {
    normalized[key.toLowerCase()] = value;
  }
  for (const name of names) {
    if (!name) {
      continue;
    }
    if (headers[name]) {
      return headers[name];
    }
    const lower = name.toLowerCase();
    if (normalized[lower]) {
      return normalized[lower];
    }
  }
  return '';
}

function extractAuth(res) {
  const sessionCookie = cookieFromResponse(
    res,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_CANDIDATES,
    (name) => name.toLowerCase().includes('session'),
  );
  const csrfCookie = cookieFromResponse(
    res,
    CSRF_COOKIE_NAME,
    CSRF_COOKIE_CANDIDATES,
    (name) => {
      const lower = name.toLowerCase();
      return lower.includes('csrf') || lower.includes('xsrf');
    },
  );
  const cookieParts = [];
  if (sessionCookie?.value) {
    cookieParts.push(`${sessionCookie.name}=${sessionCookie.value}`);
  }
  if (csrfCookie?.value) {
    cookieParts.push(`${csrfCookie.name}=${csrfCookie.value}`);
  }
  const csrfHeader =
    headerFromResponse(res.headers, [
      'X-CSRF-Token',
      'X-CSRFToken',
      'X-XSRF-TOKEN',
      'x-csrf-token',
      'x-csrftoken',
      'x-xsrf-token',
    ]) || csrfCookie?.value || '';
  return {
    sessionCookie: sessionCookie?.value || '',
    sessionCookieName: sessionCookie?.name || '',
    csrfCookie: csrfCookie?.value || '',
    csrfCookieName: csrfCookie?.name || '',
    csrfToken: csrfHeader,
    cookieHeader: cookieParts.join('; '),
  };
}

function makeParams(def, ctx) {
  const params = { tags: { endpoint: def.name, phase: def.testPhase || 'main' } };
  if (def.markExpected) {
    params.tags.expected_response = 'true';
  }
  const headers = { Accept: 'application/json' };
  if (def.headers) {
    Object.assign(headers, def.headers);
  }
  if (def.authRequired) {
    if (!ctx.auth || !ctx.auth.cookieHeader) {
      return null;
    }
    headers.Cookie = ctx.auth.cookieHeader;
    if (def.requireCsrf) {
      if (!ctx.auth.csrfToken) {
        return null;
      }
      headers['X-CSRF-Token'] = ctx.auth.csrfToken;
    }
  }
  params.headers = headers;
  return params;
}

function resolveAcceptableStatus(def) {
  if (Array.isArray(def.acceptableStatus)) {
    const allowed = new Set(def.acceptableStatus);
    return (status) => allowed.has(status);
  }
  if (typeof def.acceptableStatus === 'function') {
    return def.acceptableStatus;
  }
  return (status) => status < 400;
}

function requestEndpoint(key, ctx) {
  const def = endpointDefinitions[key];
  if (!def) {
    fail(`Unknown endpoint key: ${key}`);
  }
  if (def.requires) {
    for (const requirement of def.requires) {
      if (!resolvePath(ctx, requirement)) {
        noteSkip(key, `missing requirement ${requirement}`);
        return null;
      }
    }
  }
  const params = makeParams(def, ctx);
  if (params === null) {
    noteSkip(key, 'authentication is required but no credentials are available');
    return null;
  }

  const pathValue = typeof def.path === 'function' ? def.path(ctx) : def.path;
  const url = `${BASE_URL}${pathValue}`;
  const payload = def.body ? def.body(ctx) : null;
  if (payload && !params.headers['Content-Type']) {
    params.headers['Content-Type'] = 'application/json';
  }
  const response = http.request(def.method, url, payload, params);

  endpointLatency.add(response.timings.duration, { endpoint: def.name });
  responseBodySize.add(Number(response.body?.length || 0), { endpoint: def.name });

  const isStatusAllowed = resolveAcceptableStatus(def);
  const ok = check(response, {
    [`${def.name} ok`]: (res) => isStatusAllowed(res.status),
  });
  if (!ok) {
    console.error(`${def.name} responded with status ${response.status}`);
    endpointFailures.add(1, {
      endpoint: def.name,
      status: String(response.status),
      phase: def.testPhase || 'main',
    });
  }

  if (def.authRequired && response.headers['X-CSRF-Token']) {
    ctx.auth.csrfToken = response.headers['X-CSRF-Token'];
    if (params.headers.Cookie && !params.headers.Cookie.includes(CSRF_COOKIE_NAME)) {
      ctx.auth.cookieHeader = `${ctx.auth.cookieHeader}; ${CSRF_COOKIE_NAME}=${ctx.auth.csrfToken}`;
    }
  }

  return response;
}

function ensureUserCredentials() {
  let email = AUTH_EMAIL;
  let username = AUTH_USERNAME;
  const password = AUTH_PASSWORD;

  if (!email) {
    const stamp = Date.now();
    email = `perf-${stamp}@example.com`;
    username = username || `perf_${stamp}`;
  }
  if (!username) {
    username = email.split('@')[0];
  }

  const registerPayload = JSON.stringify({
    email,
    password,
    name_for_certificate: 'Performance Tester',
    username,
    sex: 'M',
    color: 'NS',
    role: 'User',
    birthday: '1990-01-01',
    remember: true,
  });

  const registerRes = http.post(`${BASE_URL}/auth/register`, registerPayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: {
      endpoint: 'POST /auth/register (setup)',
      expected_response: 'true',
      phase: 'setup',
    },
  });

  if (registerRes.status === 200) {
    return { auth: extractAuth(registerRes), credentials: { email, password, username } };
  }

  if (registerRes.status === 409) {
    const payload = JSON.stringify({ email, password, remember: true });
    const loginRes = http.post(`${BASE_URL}/auth/login`, payload, {
      headers: { 'Content-Type': 'application/json' },
      tags: {
        endpoint: 'POST /auth/login (setup)',
        expected_response: 'true',
        phase: 'setup',
      },
    });

    if (loginRes.status === 200) {
      return { auth: extractAuth(loginRes), credentials: { email, password, username } };
    }

    fail(`Unable to login existing test user (${loginRes.status}): ${loginRes.body}`);
  }

  if (registerRes.status >= 400) {
    fail(`Unable to register test user (${registerRes.status}): ${registerRes.body}`);
  }

  return { auth: extractAuth(registerRes), credentials: { email, password, username } };
}

function buildLoginPool(ctx) {
  const pool = [{ ...ctx.credentials }];
  const perUserLimit = Math.max(1, RATE_LIMIT_MAX_ATTEMPTS);
  const desiredPoolSizeRaw = LOGIN_USER_POOL || Math.ceil((WRITE_RATE * 60) / perUserLimit) + 3;
  const minForVus = Math.max(DEFAULT_VUS * 3, MAX_VUS * 2);
  const desiredPoolSize = Math.max(6, desiredPoolSizeRaw, minForVus);

  for (let i = pool.length; i < desiredPoolSize; i += 1) {
    const stamp = `${Date.now()}-${i}`;
    const email = `perf-${stamp}@example.com`;
    const username = `perf_${stamp}`;
    const registerPayload = JSON.stringify({
      email,
      password: AUTH_PASSWORD,
      name_for_certificate: 'Performance Tester',
      username,
      sex: 'M',
      color: 'NS',
      role: 'User',
      birthday: '1990-01-01',
      remember: true,
    });

    const registerRes = http.post(`${BASE_URL}/auth/register`, registerPayload, {
      headers: { 'Content-Type': 'application/json' },
      tags: {
        endpoint: 'POST /auth/register (login pool setup)',
        phase: 'setup',
      },
    });

    if (registerRes.status >= 400) {
      console.warn(`Failed to create login pool user (${registerRes.status}): ${registerRes.body}`);
      break;
    }

    pool.push({
      email,
      password: AUTH_PASSWORD,
      username,
    });

    sleep(0.05);
  }

  ctx.loginPool = pool;
  ctx.loginPoolSize = pool.length;
}

function hydrateDataset(ctx) {
  const dataset = {
    trailId: null,
    sectionId: null,
    itemId: null,
    formItemId: null,
    formQuestions: null,
  };

  const params =
    makeParams(
      { name: 'dataset bootstrap', authRequired: !!ctx.auth, testPhase: 'setup' },
      ctx,
    ) || {
      headers: { Accept: 'application/json' },
    };

  const trailsRes = http.get(`${BASE_URL}/trails/`, params);
  if (trailsRes.status >= 400) {
    console.warn(`Unable to list trails during setup (${trailsRes.status})`);
    return dataset;
  }
  const trailsJson = trailsRes.json();
  const firstTrail = trailsJson?.trails?.[0];
  if (!firstTrail) {
    console.warn('No trails available to benchmark. Some scenarios will be skipped.');
    return dataset;
  }

  dataset.trailId = firstTrail.id;

  const sectionsRes = http.get(`${BASE_URL}/trails/${dataset.trailId}/sections-with-items`, params);
  if (sectionsRes.status >= 400) {
    console.warn(`Unable to load sections (${sectionsRes.status})`);
    return dataset;
  }
  const sections = sectionsRes.json();
  if (Array.isArray(sections) && sections.length > 0) {
    const firstSection = sections[0];
    dataset.sectionId = firstSection?.id || null;
    if (firstSection?.items?.length) {
      const firstItem = firstSection.items[0];
      dataset.itemId = firstItem.id;
      dataset.itemType = firstItem.type || null;
      dataset.itemDurationSeconds = firstItem.duration_seconds || 0;
    }
    for (const section of sections) {
      if (!section?.items) {
        continue;
      }
      for (const item of section.items) {
        if (item.type === 'FORM') {
          dataset.formItemId = item.id;
          break;
        }
      }
      if (dataset.formItemId) {
        break;
      }
    }
  }

  if (dataset.trailId && dataset.formItemId) {
    const detailRes = http.get(
      `${BASE_URL}/trails/${dataset.trailId}/items/${dataset.formItemId}`,
      params,
    );
    if (detailRes.status < 400) {
      const detailJson = detailRes.json();
      const questions = detailJson?.form?.questions || [];
      dataset.formQuestions = questions.map((question) => ({
        id: question.id,
        firstOptionId: question.options?.length ? question.options[0].id : null,
      }));
    }
  }

  return dataset;
}

function verifyAuthRateLimit() {
  const limit = Math.max(1, RATE_LIMIT_MAX_ATTEMPTS);
  const stamp = `${Date.now()}-limit`;
  const email = `ratelimit-${stamp}@example.com`;
  const username = `ratelimit_${stamp}`;

  const registerPayload = JSON.stringify({
    email,
    password: AUTH_PASSWORD,
    name_for_certificate: 'Performance Tester',
    username,
    sex: 'M',
    role: 'User',
    birthday: '1990-01-01',
    remember: true,
  });

  const registerRes = http.post(`${BASE_URL}/auth/register`, registerPayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: {
      endpoint: 'POST /auth/register (rate limit verify)',
      expected_response: 'true',
      phase: 'setup',
    },
  });

  if (registerRes.status >= 400 && registerRes.status !== 409) {
    fail(`Unable to create rate-limit test user (${registerRes.status}): ${registerRes.body}`);
  }

  const loginPayload = JSON.stringify({ email, password: AUTH_PASSWORD, remember: true });
  const loginParams = {
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    tags: {
      endpoint: 'POST /auth/login (rate limit verify)',
      expected_response: 'true',
      rate_limit_check: 'true',
      phase: 'setup',
    },
  };

  let allowedCount = 0;
  let limitedCount = 0;
  let firstLimitedAt = -1;
  let retryAfterSeconds = 0;
  let unexpectedStatus = null;

  const attempts = limit + 3;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const response = http.post(`${BASE_URL}/auth/login`, loginPayload, loginParams);
    if (response.status === 200) {
      allowedCount += 1;
    } else if (response.status === 429) {
      limitedCount += 1;
      if (firstLimitedAt === -1) {
        firstLimitedAt = attempt;
        const retryHeader = response.headers['Retry-After'] || response.headers['retry-after'] || '0';
        retryAfterSeconds = Number(retryHeader) || 0;
      }
    } else {
      unexpectedStatus = response.status;
      break;
    }
    sleep(0.2);
  }

  if (unexpectedStatus !== null) {
    fail(`Rate limit verification encountered unexpected status ${unexpectedStatus}`);
  }

  if (limitedCount === 0) {
    fail(`Rate limiting did not trigger after ${attempts} login attempts for ${email}`);
  }

  if (firstLimitedAt < limit) {
    fail(
      `Rate limiting activated too early for ${email} (attempt ${firstLimitedAt + 1} of allowed ${limit})`,
    );
  }

  if (retryAfterSeconds <= 0 || Number.isNaN(retryAfterSeconds)) {
    fail(`Rate limit response missing valid Retry-After header for ${email}`);
  }

  console.log(
    `Rate limit verification: ${allowedCount} allowed, ${limitedCount} limited (limit=${limit}, retryAfter≈${retryAfterSeconds}s)`,
  );

  return {
    limit,
    allowedCount,
    limitedCount,
    firstLimitedAt,
    retryAfterSeconds,
    windowSeconds: RATE_LIMIT_WINDOW_SECONDS,
    email,
  };
}

export function setup() {
  const ctx = ensureUserCredentials();
  ctx.dataset = hydrateDataset(ctx);
  if (ENABLE_RATE_LIMIT_SCENARIOS) {
    buildLoginPool(ctx);
    ctx.rateLimitVerification = verifyAuthRateLimit();
  } else {
    ctx.rateLimitVerification = null;
  }

  if (ctx.dataset.trailId && ctx.auth && ctx.auth.cookieHeader) {
    const enrollParams = makeParams(
      {
        name: 'POST /user-trails/:trailId/enroll (setup)',
        method: 'POST',
        authRequired: true,
        requireCsrf: true,
      },
      ctx,
    );
    if (enrollParams) {
      http.post(`${BASE_URL}/user-trails/${ctx.dataset.trailId}/enroll`, null, enrollParams);
      sleep(0.1);
    }
  }

  return ctx;
}

function buildExec(name) {
  return function exec(data) {
    return requestEndpoint(name, data);
  };
}

export const trails_showcase = buildExec('trails_showcase');
export const trails_list = buildExec('trails_list');
export const trails_detail = buildExec('trails_detail');
export const trails_sections = buildExec('trails_sections');
export const trails_section_items = buildExec('trails_section_items');
export const trails_sections_with_items = buildExec('trails_sections_with_items');
export const trails_included_items = buildExec('trails_included_items');
export const trails_requirements = buildExec('trails_requirements');
export const trails_audience = buildExec('trails_audience');
export const trails_learn = buildExec('trails_learn');
export const trail_item_detail = buildExec('trail_item_detail');
export const auth_login = buildExec('auth_login');
export const user_trail_enroll = buildExec('user_trail_enroll');
export const user_trail_progress = buildExec('user_trail_progress');
export const user_trail_items_progress = buildExec('user_trail_items_progress');
export const user_trail_sections_progress = buildExec('user_trail_sections_progress');
export const me_profile = buildExec('me_profile');
export const trail_item_progress = buildExec('trail_item_progress');
export const trail_form_submission = buildExec('trail_form_submission');

export function handleSummary(data) {
  const durationSeconds = data.state?.testRunDurationMs ? data.state.testRunDurationMs / 1000 : 0;
  const totalRequests = data.metrics?.http_reqs?.values?.count || 0;
  const rps = durationSeconds ? totalRequests / durationSeconds : 0;
  const rpm = rps * 60;
  const steadyStateSeconds = DEFAULT_SECONDS || durationSeconds;
  const steadyStateRps = steadyStateSeconds ? totalRequests / steadyStateSeconds : 0;
  const nonSteadySeconds = WARMUP_SECONDS + COOLDOWN_SECONDS + FINAL_STAGE_SECONDS;
  const nonSteadyShare = durationSeconds
    ? Math.min(100, Math.max(0, (nonSteadySeconds / durationSeconds) * 100))
    : 0;
  const totalBytesReceived = data.metrics?.data_received?.values?.sum || 0;
  const throughputBytesPerSecond = durationSeconds
    ? totalBytesReceived / durationSeconds
    : 0;
  const throughputKibPerSecond = throughputBytesPerSecond / 1024;

  const rateLimitInfo = data.state?.rateLimitVerification;
  const failureMetric = data.metrics?.endpoint_failures;

  const parseTagKey = (key) => {
    if (!key) {
      return {};
    }
    const match = key.match(/\{([^}]*)}$/);
    const tagPortion = match ? match[1] : key;
    if (!tagPortion) {
      return {};
    }

    const tags = {};
    for (const rawPart of tagPortion.split(',')) {
      const part = rawPart.trim();
      if (!part) {
        continue;
      }
      const [name, ...rest] = part.split(':');
      if (!name) {
        continue;
      }
      tags[name.trim()] = rest.join(':').trim();
    }
    return tags;
  };

  let mainPhaseFailureLine = null;
  let mainPhaseFailureDetails = [];
  let writePhaseFailureLine = null;
  let writePhaseFailureDetails = [];

  if (failureMetric?.submetrics) {
    const breakdown = Object.entries(failureMetric.submetrics).map(([tagKey, metric]) => {
      const tags = parseTagKey(tagKey);
      return {
        endpoint: tags.endpoint || 'unknown',
        phase: tags.phase || 'main',
        status: tags.status || 'unknown',
        count: metric.values?.count || 0,
      };
    });

    const mainBreakdown = breakdown
      .filter((entry) => entry.phase === 'main' && entry.count > 0)
      .sort((a, b) => b.count - a.count);

    if (mainBreakdown.length > 0) {
      const totalFailures = mainBreakdown.reduce((sum, entry) => sum + entry.count, 0);
      mainPhaseFailureLine = `Main phase failures: ${totalFailures}`;
      mainPhaseFailureDetails = mainBreakdown.slice(0, 5);
    }

    const writeBreakdown = breakdown
      .filter((entry) => entry.phase === 'write' && entry.count > 0)
      .sort((a, b) => b.count - a.count);

    if (writeBreakdown.length > 0) {
      const totalFailures = writeBreakdown.reduce((sum, entry) => sum + entry.count, 0);
      writePhaseFailureLine = `Write phase failures: ${totalFailures}`;
      writePhaseFailureDetails = writeBreakdown.slice(0, 5);
    }
  }

  const summaryLines = [
    '========== Performance Summary ==========',
    ENABLE_RATE_LIMIT_SCENARIOS
      ? rateLimitInfo
        ? `Auth rate limit: ${rateLimitInfo.allowedCount} allowed before ${rateLimitInfo.limitedCount} limited (limit=${rateLimitInfo.limit}, retry-after≈${rateLimitInfo.retryAfterSeconds}s)`
        : 'Auth rate limit: verification unavailable'
      : 'Auth rate limit: skipped (ENABLE_RATE_LIMIT_SCENARIOS=false)',
    `Test duration: ${durationSeconds.toFixed(2)}s`,
    `Total HTTP requests: ${totalRequests}`,
    `Estimated RPS: ${rps.toFixed(2)}`,
    `Estimated RPM: ${rpm.toFixed(2)}`,
    steadyStateSeconds
      ? `Approx steady-state RPS (main stage): ${steadyStateRps.toFixed(2)}`
      : null,
    durationSeconds
      ? `Warmup/cooldown share: ${nonSteadyShare.toFixed(1)}% of test time`
      : null,
    `Throughput: ${throughputBytesPerSecond.toFixed(2)} B/s (${throughputKibPerSecond.toFixed(2)} KiB/s)`,
    mainPhaseFailureLine,
    writePhaseFailureLine,
    '==========================================',
  ];

  const summaryText = `${summaryLines.filter(Boolean).join('\n')}\n`;
  return {
    stdout: summaryText,
    'performance/results.json': JSON.stringify(
      {
        duration_seconds: durationSeconds,
        total_requests: totalRequests,
        requests_per_second: rps,
        requests_per_minute: rpm,
        throughput_bytes_per_second: throughputBytesPerSecond,
        throughput_kib_per_second: throughputKibPerSecond,
        rate_limit_verification_enabled: ENABLE_RATE_LIMIT_SCENARIOS,
        rate_limit_verification: rateLimitInfo || null,
        main_phase_failures: mainPhaseFailureDetails,
        write_phase_failures: writePhaseFailureDetails,
        steady_state_seconds: steadyStateSeconds,
        steady_state_rps: steadyStateRps,
        non_steady_phase_seconds: nonSteadySeconds,
        non_steady_phase_share_percent: nonSteadyShare,
      },
      null,
      2,
    ),
  };
}
