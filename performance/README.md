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
| `BASE_URL` | `https://127.0.0.1:8001` | Base URL of the API under test. |
| `INSECURE_SKIP_TLS_VERIFY` | `true` | Skip TLS verification for self-signed dev certificates; set to `false` for trusted endpoints. |
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

### Discovering the sustainable RPS ceiling

When you want to understand how much throughput the platform can handle before error
rates spike, execute the RPS probe. It reuses the same authentication/bootstrap logic as
the main load test but gradually increases the target arrival rate until it breaches the
configured failure tolerance (default 1% of requests):

```bash
k6 run performance/k6/rps_probe.test.js
```

Tweak the sweep parameters via environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `MIN_PROBE_RPS` | `10` | Initial RPS target after warm-up. |
| `MAX_PROBE_RPS` | `200` | Maximum target RPS to try before stopping. |
| `PROBE_STEP_RPS` | `10` | Increment applied to the target RPS between steps. |
| `PROBE_WARMUP_DURATION` | `30s` | Length of the warm-up stage at `MIN_PROBE_RPS`. |
| `PROBE_STEP_DURATION` | `30s` | How long each target RPS level is exercised. |
| `PROBE_STEP_PAUSE` | `5s` | Gap between successive RPS levels to let the system stabilise. |
| `PROBE_FAILURE_TOLERANCE` | `0.01` | Maximum acceptable failure rate (e.g. `0.05` = 5%). |

At the end of the run the script prints a per-level summary and stores the raw numbers in
`performance/rps_results.json`, including the highest RPS target that stayed within the
failure threshold.

### Progress endpoints probe

To stress just the `/user-trails/.../progress` family (the most frequent calls in
production) run:

```bash
k6 run performance/k6/progress_probe.test.js
```

Key env overrides:

| Variable | Default | Description |
| --- | --- | --- |
| `PROGRESS_MIN_RPS` | `10` | Initial arrival rate after warmup. |
| `PROGRESS_MAX_RPS` | `80` | Final target RPS to probe. |
| `PROGRESS_STEP_RPS` | `10` | Increment between stages. |
| `PROGRESS_STEP_DURATION` | `45s` | Duration of each target plateau. |
| `PROGRESS_WARMUP_DURATION` | `30s` | Warmup before the first measurement stage. |
| `PROGRESS_FAILURE_TOLERANCE` | `0.01` | Allowed failure rate before declaring the step as failed. |

Results are written to `performance/progress_probe_results.json` and the CLI summary
highlights the highest passing target.

### Progress write probe

When you only need to exercise the video progress write endpoint (PUT
`/trails/:trailId/items/:itemId/progress`), run:

```bash
k6 run performance/k6/progress_write.test.js
```

Environment overrides:

| Variable | Default | Description |
| --- | --- | --- |
| `PROGRESS_WRITE_RPS` | `15` | Target arrival rate for the write scenario. |
| `PROGRESS_WRITE_DURATION` | `2m` | Steady-state duration at the target rate. |
| `PROGRESS_WRITE_WARMUP` | `30s` | Ramp-up period before hitting the target rate. |
| `PROGRESS_WRITE_COOLDOWN` | `30s` | Cooldown period after the main phase. |
| `PROGRESS_WRITE_PRE_ALLOCATED_VUS` | `20` | Pre-allocated virtual users for the scenario. |
| `PROGRESS_WRITE_MAX_VUS` | `80` | Maximum virtual users k6 can scale to during the run. |
| `PROGRESS_WRITE_FAILURE_TOLERANCE` | `0.02` | Maximum acceptable failure rate before the test aborts. |

The script reuses the same bootstrap routine as the other probes (login, trail
enrolment and dataset hydration) and writes a summary report to
`performance/progress_write_results.json`.

#### Measuring memory usage during the run

The helper script `scripts/monitor_memory.py` samples RSS/VMS of the uvicorn worker while
the probe executes. Install psutil (`pip install psutil`) and run it in parallel:

```bash
python scripts/monitor_memory.py --pattern "uvicorn app.asgi:app" \
  --interval 0.5 --duration 420 --output perf_progress_mem.csv
```

This logs the memory footprint every 0.5 s and stores the data in CSV for later analysis.
Start the monitor a few seconds before the k6 command so the timeline covers warmup and
steady-state phases.

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
