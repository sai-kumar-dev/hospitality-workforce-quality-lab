"""Parse Locust CSV output and enforce documented smoke thresholds."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class PerformanceThresholds(BaseModel):
    """Initial local/CI regression-smoke thresholds."""

    model_config = ConfigDict(extra="forbid")

    max_failure_rate_percent: float = Field(default=1.0, ge=0.0, le=100.0)
    max_jobs_p95_ms: float = Field(default=1_000.0, gt=0.0)
    max_health_p95_ms: float = Field(default=300.0, gt=0.0)


class LocustMetric(BaseModel):
    """Relevant values from one Locust stats row."""

    model_config = ConfigDict(extra="forbid")

    name: str
    request_count: int
    failure_count: int
    p95_ms: float


class ThresholdReport(BaseModel):
    """Machine-readable quality-gate result."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    failure_rate_percent: float
    metrics: list[LocustMetric]
    violations: list[str]


def _integer(value: str | None) -> int:
    return int(float(value or "0"))


def _number(value: str | None) -> float:
    return float(value or "0")


def read_locust_stats(path: Path) -> list[LocustMetric]:
    """Read `<prefix>_stats.csv` using Locust's stable header names."""
    with path.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        return [
            LocustMetric(
                name=row.get("Name", ""),
                request_count=_integer(row.get("Request Count")),
                failure_count=_integer(row.get("Failure Count")),
                p95_ms=_number(row.get("95%")),
            )
            for row in rows
        ]


def evaluate_thresholds(
    metrics: list[LocustMetric],
    thresholds: PerformanceThresholds,
) -> ThresholdReport:
    """Evaluate failure-rate, jobs-list p95, and liveness p95 thresholds."""
    aggregate = next((metric for metric in metrics if metric.name == "Aggregated"), None)
    if aggregate is None:
        request_count = sum(metric.request_count for metric in metrics)
        failure_count = sum(metric.failure_count for metric in metrics)
    else:
        request_count = aggregate.request_count
        failure_count = aggregate.failure_count
    failure_rate = (failure_count / request_count * 100.0) if request_count else 100.0
    violations: list[str] = []
    if failure_rate >= thresholds.max_failure_rate_percent:
        violations.append(
            f"Failure rate {failure_rate:.2f}% must be below "
            f"{thresholds.max_failure_rate_percent:.2f}%"
        )
    jobs = [
        metric
        for metric in metrics
        if metric.name == "/api/jobs" or metric.name.startswith("/api/jobs?")
    ]
    health = [metric for metric in metrics if metric.name == "/health/live"]
    if not jobs:
        violations.append("Missing required /api/jobs metric")
    elif max(metric.p95_ms for metric in jobs) > thresholds.max_jobs_p95_ms:
        violations.append(
            f"Jobs-list p95 {max(metric.p95_ms for metric in jobs):.0f}ms exceeds "
            f"{thresholds.max_jobs_p95_ms:.0f}ms"
        )
    if not health:
        violations.append("Missing required /health/live metric")
    elif max(metric.p95_ms for metric in health) > thresholds.max_health_p95_ms:
        violations.append(
            f"Health p95 {max(metric.p95_ms for metric in health):.0f}ms exceeds "
            f"{thresholds.max_health_p95_ms:.0f}ms"
        )
    return ThresholdReport(
        passed=not violations,
        failure_rate_percent=failure_rate,
        metrics=metrics,
        violations=violations,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the threshold CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats_csv", type=Path, nargs="?")
    parser.add_argument(
        "--stats",
        dest="stats_option",
        type=Path,
        help="Locust `<prefix>_stats.csv` output",
    )
    parser.add_argument("--max-failure-rate", type=float, default=1.0)
    parser.add_argument("--max-jobs-p95-ms", type=float, default=1_000.0)
    parser.add_argument("--max-health-p95-ms", type=float, default=300.0)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> None:
    """CLI entry point used by local and CI performance profiles."""
    arguments = build_parser().parse_args()
    stats_path = arguments.stats_option or arguments.stats_csv
    if stats_path is None:
        build_parser().error("a Locust stats CSV is required via --stats or positional input")
    thresholds = PerformanceThresholds(
        max_failure_rate_percent=arguments.max_failure_rate,
        max_jobs_p95_ms=arguments.max_jobs_p95_ms,
        max_health_p95_ms=arguments.max_health_p95_ms,
    )
    try:
        report = evaluate_thresholds(read_locust_stats(stats_path), thresholds)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Could not parse Locust stats: {error}\n")
        raise SystemExit(2) from error
    output = report.model_dump_json(indent=2)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(output, encoding="utf-8")
    sys.stdout.write(f"{json.dumps(report.model_dump(mode='json'), indent=2)}\n")
    raise SystemExit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
