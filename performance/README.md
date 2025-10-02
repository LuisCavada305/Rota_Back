# Performance Benchmarks

This folder contains two complementary benchmarking tools:

1. A **k6 load test** that exercises every public HTTP endpoint and reports throughput
   metrics such as RPS (requests per second) and RPM (requests per minute).
2. A **database query benchmark** that measures how fast each repository method runs so
   you can estimate internal query throughput.

Both tools assume the API server is already running and that the database contains the
lookup rows required by the application. They automatically provision a synthetic test
user if one does not exist so they can authenticate safely.

## k6 endpoint benchmark

Run the load test against a running server (default `http://localhost:5000`):

```bash
k6 run performance/k6/performance.test.js
```

Environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `BASE_URL` | `http://localhost:5000` | Base URL of the API under test. |
| `AUTH_EMAIL` | auto-generated | Email for the synthetic load-test user. Existing credentials are reused when provided. |
| `AUTH_PASSWORD` | `PerfTest@123` | Password for the synthetic user (used when creating or logging in). |
| `AUTH_USERNAME` | derived from email | Username for the synthetic user. |
| `TARGET_RPS` | `5` | Target arrival rate (requests per second) for each scenario. |
| `TEST_DURATION` | `1m` | Duration of each scenario. |
| `PRE_ALLOCATED_VUS` | `20` | Pre-allocated virtual users for the constant-arrival executor. |
| `ENABLE_WRITE_SCENARIOS` | `true` | Set to `false` to skip write-heavy endpoints (progress updates, form submissions). |
| `SESSION_COOKIE_NAME` | `rota_session` | Override the session cookie name if your deployment customises it. |
| `CSRF_COOKIE_NAME` | `rota_csrf` | Override the CSRF cookie name if your deployment customises it. |

The script automatically logs in (or registers) the synthetic user, enrolls in the first
available trail, and then runs a dedicated scenario per endpoint. At the end of the run
it prints a consolidated summary containing:

- Total runtime
- Total number of HTTP requests
- Estimated RPS and RPM
- Network throughput (bytes/second and KiB/second)

The raw metrics are also written to `performance/results.json` so you can archive them or
feed them into dashboards.

## Repository query benchmark

Run the Python benchmark to measure ORM query performance:

```bash
python performance/db_benchmark.py --iterations 100 --warmup 10 --json performance/db_results.json
```

Key options:

| Option | Description |
| --- | --- |
| `--iterations` | Number of measured iterations per repository method (default `50`). |
| `--warmup` | Warm-up iterations per method that are discarded from the results (default `5`). |
| `--include-writes` | Include benchmarks that perform database writes (disabled by default). |
| `--user-email` / `--user-password` | Credentials used for the synthetic benchmark user. |
| `--json` | Path to a JSON file where the script should dump the raw metrics. |

The script ensures the lookup tables contain the expected codes, creates/reuses a test
user, and then executes every repository method. For each query it reports:

- Average latency per call (ms)
- Operations per second and per minute
- Rows processed per second (when applicable)

An aggregated summary at the end shows the combined throughput across all executed
queries. Use the JSON output to track historical trends or feed the measurements into
CI pipelines.
