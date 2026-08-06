"""Unit tests for deterministic failure triage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from shiftbridge_qa.diagnostics.triage import (
    Confidence,
    Layer,
    build_parser,
    classify,
    generate_report,
    write_report,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_triage_classifies_network_evidence_transparently() -> None:
    layer, confidence, action = classify(
        "Request aborted: net::ERR_CONNECTION_REFUSED while calling /api/jobs"
    )

    assert layer is Layer.NETWORK
    assert confidence is Confidence.HIGH
    assert "reachability" in action


def test_triage_groups_equivalent_junit_failures_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0"?>
<testsuite tests="2" failures="2">
  <testcase classname="qa.ui" name="first">
    <failure message="Locator timeout at localhost:41001 line 20 password=one" />
  </testcase>
  <testcase classname="qa.ui" name="second">
    <failure message="Locator timeout at localhost:41002 line 99 password=two" />
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )

    report = generate_report(junit)

    assert report.failure_count == 2
    assert report.signature_group_count == 1
    assert report.failures[0].similar_failures == ["qa.ui::second"]
    assert "one" not in json.dumps(report.model_dump(mode="json"))


def test_triage_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<testsuite tests="1" failures="1"><testcase name="api">
<failure message="HTTP 500 from /api/jobs" /></testcase></testsuite>""",
        encoding="utf-8",
    )

    paths = write_report(generate_report(junit), tmp_path / "triage")

    assert all(path.exists() for path in paths)
    assert "Probable layer: API" in paths[1].read_text(encoding="utf-8")


def test_triage_cli_accepts_makefile_and_ci_named_options(tmp_path: Path) -> None:
    arguments = build_parser().parse_args(
        [
            "--junit",
            str(tmp_path / "junit"),
            "--console",
            str(tmp_path / "browser"),
            "--http",
            str(tmp_path / "http"),
            "--output",
            str(tmp_path / "triage"),
        ]
    )

    assert arguments.junit_option == tmp_path / "junit"
    assert arguments.console == [tmp_path / "browser"]
    assert arguments.http == [tmp_path / "http"]
    assert arguments.output_dir == tmp_path / "triage"


def test_triage_aggregates_multiple_junit_files_from_a_directory(tmp_path: Path) -> None:
    junit_dir = tmp_path / "junit"
    junit_dir.mkdir()
    for index, message in enumerate(("HTTP 500 from /api/jobs", "Locator not visible")):
        (junit_dir / f"suite-{index}.xml").write_text(
            f"""<testsuite tests="1" failures="1"><testcase name="case-{index}">
<failure message="{message}" /></testcase></testsuite>""",
            encoding="utf-8",
        )

    report = generate_report(junit_dir)

    assert report.failure_count == 2
    assert {failure.test_name for failure in report.failures} == {"case-0", "case-1"}
