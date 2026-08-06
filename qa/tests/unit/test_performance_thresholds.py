"""Unit tests for Locust regression-smoke thresholds."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from shiftbridge_qa.diagnostics.performance import (
    LocustMetric,
    PerformanceThresholds,
    build_parser,
    evaluate_thresholds,
    read_locust_stats,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def healthy_metrics() -> list[LocustMetric]:
    return [
        LocustMetric(name="/api/jobs", request_count=80, failure_count=0, p95_ms=220),
        LocustMetric(name="/health/live", request_count=20, failure_count=0, p95_ms=40),
        LocustMetric(name="Aggregated", request_count=100, failure_count=0, p95_ms=200),
    ]


def test_performance_threshold_parser_accepts_a_healthy_smoke_run() -> None:
    report = evaluate_thresholds(healthy_metrics(), PerformanceThresholds())

    assert report.passed is True
    assert report.failure_rate_percent == 0
    assert report.violations == []


def test_performance_threshold_parser_reports_each_exceeded_gate() -> None:
    metrics = [
        LocustMetric(name="/api/jobs", request_count=80, failure_count=2, p95_ms=1_500),
        LocustMetric(name="/health/live", request_count=20, failure_count=0, p95_ms=500),
        LocustMetric(name="Aggregated", request_count=100, failure_count=2, p95_ms=1_000),
    ]

    report = evaluate_thresholds(metrics, PerformanceThresholds())

    assert report.passed is False
    assert len(report.violations) == 3


def test_locust_csv_reader_uses_named_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "locust_stats.csv"
    csv_path.write_text(
        "Type,Name,Request Count,Failure Count,95%\n"
        "GET,/api/jobs,12,0,125\n"
        "GET,/health/live,3,0,20\n",
        encoding="utf-8",
    )

    metrics = read_locust_stats(csv_path)

    assert metrics[0].name == "/api/jobs"
    assert metrics[0].p95_ms == 125


def test_performance_cli_accepts_makefile_and_workflow_stats_flag(tmp_path: Path) -> None:
    stats = tmp_path / "locust_stats.csv"

    arguments = build_parser().parse_args(["--stats", str(stats)])

    assert arguments.stats_option == stats
