# ShiftBridge performance smoke

These profiles are regression checks for the local fictional application, not capacity
benchmarks. GitHub-hosted runner timing is noisy.

- Local: `locust -f qa/performance/locustfile.py --config qa/performance/profiles/local-smoke.conf`
- CI: `locust -f qa/performance/locustfile.py --config qa/performance/profiles/ci-smoke.conf`
- Manual: start with `manual-deeper.conf` and override `--users`, `--spawn-rate`, or
  `--run-time` explicitly.

Evaluate the CSV with:

```text
shiftbridge-performance-thresholds artifacts/performance/local/locust_stats.csv
```

The initial gates are an aggregate failure rate below 1%, jobs-list p95 at or below
1000 ms, and liveness p95 at or below 300 ms.

