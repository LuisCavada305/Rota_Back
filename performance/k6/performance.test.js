import http from 'k6/http';
import { check, fail, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';
const AUTH_EMAIL = __ENV.AUTH_EMAIL || '';
const AUTH_PASSWORD = __ENV.AUTH_PASSWORD || 'PerfTest@123';
const AUTH_USERNAME = __ENV.AUTH_USERNAME || '';
const DEFAULT_RATE = Number(__ENV.TARGET_RPS || 5);
const DEFAULT_DURATION = __ENV.TEST_DURATION || '1m';
const DEFAULT_VUS = Number(__ENV.PRE_ALLOCATED_VUS || 20);
const ENABLE_WRITE_SCENARIOS = (__ENV.ENABLE_WRITE_SCENARIOS || 'true').toLowerCase() !== 'false';
const SESSION_COOKIE_NAME = __ENV.SESSION_COOKIE_NAME || 'rota_session';
const CSRF_COOKIE_NAME = __ENV.CSRF_COOKIE_NAME || 'rota_csrf';

const BASE_SCENARIO = {
  executor: 'constant-arrival-rate',
  rate: DEFAULT_RATE,
  timeUnit: '1s',
  duration: DEFAULT_DURATION,
  preAllocatedVUs: DEFAULT_VUS,
  gracefulStop: '10s',
};

const endpointLatency = new Trend('endpoint_duration_ms', true);
const responseBodySize = new Trend('response_body_bytes', true);
const skipNotices = {};

function scenario(definitionOverrides = {}) {
  return Object.assign({}, BASE_SCENARIO, definitionOverrides);
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
    requires: ['dataset.trailId', 'dataset.itemId'],
  },
  auth_login: {
    name: 'POST /auth/login',
    method: 'POST',
    path: () => '/auth/login',
    headers: { 'Content-Type': 'application/json' },
    body: (ctx) => JSON.stringify({
      email: ctx.credentials.email,
      password: ctx.credentials.password,
      remember: true,
    }),
  },
  user_trail_enroll: {
    name: 'POST /user-trails/:trailId/enroll',
    method: 'POST',
    path: (ctx) => `/user-trails/${ctx.dataset.trailId}/enroll`,
    requires: ['dataset.trailId'],
    authRequired: true,
    requireCsrf: true,
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
    body: () => JSON.stringify({
      status: 'COMPLETED',
      progress_value: 100,
    }),
  },
  trail_form_submission: {
    name: 'POST /trails/:id/items/:itemId/form-submissions',
    method: 'POST',
    path: (ctx) => `/trails/${ctx.dataset.trailId}/items/${ctx.dataset.formItemId}/form-submissions`,
    requires: ['dataset.trailId', 'dataset.formItemId', 'dataset.formQuestions'],
    authRequired: true,
    requireCsrf: true,
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

export const options = {
  scenarios: {
    trails_showcase: scenario({ exec: 'trails_showcase' }),
    trails_list: scenario({ exec: 'trails_list' }),
    trails_detail: scenario({ exec: 'trails_detail' }),
    trails_sections: scenario({ exec: 'trails_sections' }),
    trails_section_items: scenario({ exec: 'trails_section_items' }),
    trails_sections_with_items: scenario({ exec: 'trails_sections_with_items' }),
    trails_included_items: scenario({ exec: 'trails_included_items' }),
    trails_requirements: scenario({ exec: 'trails_requirements' }),
    trails_audience: scenario({ exec: 'trails_audience' }),
    trails_learn: scenario({ exec: 'trails_learn' }),
    trail_item_detail: scenario({ exec: 'trail_item_detail' }),
    auth_login: scenario({ exec: 'auth_login' }),
    user_trail_enroll: scenario({ exec: 'user_trail_enroll', gracefulStop: '0s' }),
    user_trail_progress: scenario({ exec: 'user_trail_progress' }),
    user_trail_items_progress: scenario({ exec: 'user_trail_items_progress' }),
    user_trail_sections_progress: scenario({ exec: 'user_trail_sections_progress' }),
    me_profile: scenario({ exec: 'me_profile' }),
  },
};

if (ENABLE_WRITE_SCENARIOS) {
  options.scenarios.trail_item_progress = scenario({ exec: 'trail_item_progress' });
  options.scenarios.trail_form_submission = scenario({ exec: 'trail_form_submission' });
}

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

function cookieFromResponse(res, cookieName) {
  const cookie = res.cookies?.[cookieName];
  if (!cookie || cookie.length === 0) {
    return '';
  }
  return cookie[cookie.length - 1].value;
}

function extractAuth(res) {
  const sessionCookie = cookieFromResponse(res, SESSION_COOKIE_NAME);
  const csrfCookie = cookieFromResponse(res, CSRF_COOKIE_NAME);
  const cookieParts = [];
  if (sessionCookie) {
    cookieParts.push(`${SESSION_COOKIE_NAME}=${sessionCookie}`);
  }
  if (csrfCookie) {
    cookieParts.push(`${CSRF_COOKIE_NAME}=${csrfCookie}`);
  }
  const csrfHeader = res.headers['X-CSRF-Token'] || res.headers['x-csrf-token'] || csrfCookie;
  return {
    sessionCookie,
    csrfCookie,
    csrfToken: csrfHeader,
    cookieHeader: cookieParts.join('; '),
  };
}

function makeParams(def, ctx) {
  const params = { tags: { endpoint: def.name } };
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

  const ok = check(response, {
    [`${def.name} < 400`]: (res) => res.status < 400,
  });
  if (!ok) {
    console.error(`${def.name} responded with status ${response.status}`);
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

  const payload = JSON.stringify({ email, password, remember: true });
  const loginRes = http.post(`${BASE_URL}/auth/login`, payload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { endpoint: 'POST /auth/login (setup)' },
  });

  if (loginRes.status === 200) {
    return { auth: extractAuth(loginRes), credentials: { email, password, username } };
  }

  if (loginRes.status !== 401) {
    fail(`Unable to login (${loginRes.status}): ${loginRes.body}`);
  }

  const registerPayload = JSON.stringify({
    email,
    password,
    name_for_certificate: 'Performance Tester',
    username,
    sex: 'M',
    role: 'User',
    birthday: '1990-01-01',
    remember: true,
  });

  const registerRes = http.post(`${BASE_URL}/auth/register`, registerPayload, {
    headers: { 'Content-Type': 'application/json' },
    tags: { endpoint: 'POST /auth/register (setup)' },
  });

  if (registerRes.status >= 400) {
    fail(`Unable to register test user (${registerRes.status}): ${registerRes.body}`);
  }

  return { auth: extractAuth(registerRes), credentials: { email, password, username } };
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
    makeParams({ name: 'dataset bootstrap', authRequired: !!ctx.auth }, ctx) || {
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
      dataset.itemId = firstSection.items[0].id;
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

export function setup() {
  const ctx = ensureUserCredentials();
  ctx.dataset = hydrateDataset(ctx);

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
    requestEndpoint(name, data);
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
  const totalRequests = data.metrics?.http_reqs?.count || 0;
  const rps = durationSeconds ? totalRequests / durationSeconds : 0;
  const rpm = rps * 60;
  const throughputBytesPerSecond = durationSeconds
    ? (data.metrics?.data_received?.sum || 0) / durationSeconds
    : 0;
  const throughputKibPerSecond = throughputBytesPerSecond / 1024;

  const summaryLines = [
    '========== Performance Summary ==========',
    `Test duration: ${durationSeconds.toFixed(2)}s`,
    `Total HTTP requests: ${totalRequests}`,
    `Estimated RPS: ${rps.toFixed(2)}`,
    `Estimated RPM: ${rpm.toFixed(2)}`,
    `Throughput: ${throughputBytesPerSecond.toFixed(2)} B/s (${throughputKibPerSecond.toFixed(2)} KiB/s)`,
    '==========================================',
  ];

  const summaryText = `${summaryLines.join('\n')}\n`;
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
      },
      null,
      2,
    ),
  };
}
