"""Deterministic JUnit and browser-evidence failure triage."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from shiftbridge_qa.diagnostics.redaction import redact, redact_text
from shiftbridge_qa.diagnostics.signatures import normalize_signature


class Layer(StrEnum):
    """Probable origin of a failure."""

    TEST_CODE = "Test code"
    UI = "UI"
    API = "API"
    DATABASE = "Database"
    ENVIRONMENT = "Environment"
    NETWORK = "Network"
    UNKNOWN = "Unknown"


class Confidence(StrEnum):
    """Rule-match confidence."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FailureTriage(BaseModel):
    """One classified test failure."""

    model_config = ConfigDict(extra="forbid")

    test_name: str
    failure_signature: str
    probable_layer: Layer
    evidence: list[str]
    related_artifact_paths: list[str]
    similar_failures: list[str] = Field(default_factory=list)
    suggested_first_action: str
    confidence: Confidence


class TriageReport(BaseModel):
    """Serializable triage result for one test run."""

    model_config = ConfigDict(extra="forbid")

    source_junit: str
    failure_count: int
    signature_group_count: int
    failures: list[FailureTriage]


_RULES: tuple[tuple[Layer, tuple[str, ...], str], ...] = (
    (
        Layer.NETWORK,
        ("connection refused", "name or service not known", "net::err_", "request aborted", "dns"),
        "Check service reachability, proxy/DNS state, and the failed-request artifact.",
    ),
    (
        Layer.DATABASE,
        ("integrityerror", "sqlalchemy", "postgres", "deadlock", "database"),
        "Inspect database health and sanitized service logs for the correlated request.",
    ),
    (
        Layer.ENVIRONMENT,
        ("browser executable", "no space left", "service unavailable", "docker", "503"),
        "Verify stack health, runner resources, and browser/dependency installation.",
    ),
    (
        Layer.UI,
        ("locator", "strict mode violation", "not visible", "page crashed", "aria", "element"),
        "Open the Playwright trace and compare rendered semantics with the page object.",
    ),
    (
        Layer.API,
        ("http 4", "http 5", "status code", "problem+json", "/api/", "response body"),
        "Use the request ID to inspect API logs and replay the sanitized request.",
    ),
    (
        Layer.TEST_CODE,
        ("fixture", "typeerror", "attributeerror", "assertionerror", "collection error"),
        "Inspect the failing assertion and fixture setup before changing product code.",
    ),
)


def classify(message: str) -> tuple[Layer, Confidence, str]:
    """Classify a message through transparent keyword rules."""
    normalized = normalize_signature(message)
    for layer, keywords, action in _RULES:
        matches = sum(keyword in normalized for keyword in keywords)
        if matches:
            confidence = Confidence.HIGH if matches >= 2 else Confidence.MEDIUM
            return layer, confidence, action
    return (
        Layer.UNKNOWN,
        Confidence.LOW,
        "Start with the complete traceback and correlate browser, API, and service evidence.",
    )


def _artifact_properties(testcase: ET.Element) -> list[str]:
    properties = testcase.find("properties")
    if properties is None:
        return []
    paths: list[str] = []
    for item in properties.findall("property"):
        name = item.get("name", "").lower()
        value = item.get("value")
        if value and any(word in name for word in ("artifact", "screenshot", "trace", "video")):
            paths.append(value)
    return paths


def parse_junit(path: Path) -> list[FailureTriage]:
    """Parse pytest-compatible JUnit XML without modifying source artifacts."""
    xml_source = path.read_text(encoding="utf-8")
    if "<!DOCTYPE" in xml_source.upper() or "<!ENTITY" in xml_source.upper():
        msg = "JUnit XML must not contain DTD or entity declarations"
        raise ET.ParseError(msg)
    root = ET.fromstring(xml_source)  # noqa: S314 - DTD/entity declarations rejected above
    failures: list[FailureTriage] = []
    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")
        if failure is None:
            failure = testcase.find("error")
        if failure is None:
            continue
        class_name = testcase.get("classname", "")
        case_name = testcase.get("name", "<unnamed>")
        test_name = f"{class_name}::{case_name}" if class_name else case_name
        message = "\n".join(part for part in (failure.get("message"), failure.text) if part)
        safe_message = redact_text(message)[:4_000]
        layer, confidence, action = classify(safe_message)
        failures.append(
            FailureTriage(
                test_name=test_name,
                failure_signature=normalize_signature(safe_message),
                probable_layer=layer,
                evidence=[safe_message],
                related_artifact_paths=_artifact_properties(testcase),
                suggested_first_action=action,
                confidence=confidence,
            )
        )
    return failures


def _load_optional_evidence(paths: list[Path]) -> list[str]:
    evidence: list[str] = []
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(
                item
                for pattern in ("*.json", "*.log", "*.txt")
                for item in path.rglob(pattern)
                if item.is_file()
            )
        else:
            expanded.append(path)
    for path in expanded:
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            evidence.append(redact_text(raw[:2_000]))
        else:
            evidence.append(json.dumps(redact(parsed), sort_keys=True)[:2_000])
    return evidence


def generate_report(
    junit_path: Path,
    *,
    evidence_paths: list[Path] | None = None,
) -> TriageReport:
    """Generate and group deterministic failure classifications."""
    if junit_path.is_dir():
        junit_files = sorted(junit_path.rglob("*.xml"))
        if not junit_files:
            msg = f"No JUnit XML files found under {junit_path}"
            raise FileNotFoundError(msg)
    else:
        junit_files = [junit_path]
    failures = [failure for path in junit_files for failure in parse_junit(path)]
    extra_evidence = _load_optional_evidence(evidence_paths or [])
    by_signature: dict[str, list[FailureTriage]] = {}
    for failure in failures:
        by_signature.setdefault(failure.failure_signature, []).append(failure)
        failure.evidence.extend(extra_evidence)
    for group in by_signature.values():
        names = [failure.test_name for failure in group]
        for failure in group:
            failure.similar_failures = [name for name in names if name != failure.test_name]
    return TriageReport(
        source_junit=str(junit_path),
        failure_count=len(failures),
        signature_group_count=len(by_signature),
        failures=failures,
    )


def render_markdown(report: TriageReport) -> str:
    """Render the JSON model into a concise human-readable report."""
    lines = [
        "# ShiftBridge failure triage",
        "",
        f"- Failures: {report.failure_count}",
        f"- Signature groups: {report.signature_group_count}",
        f"- Source: `{report.source_junit}`",
        "",
    ]
    for failure in report.failures:
        lines.extend(
            [
                f"## {failure.test_name}",
                "",
                f"- Probable layer: {failure.probable_layer.value}",
                f"- Confidence: {failure.confidence.value}",
                f"- Signature: `{failure.failure_signature}`",
                f"- First action: {failure.suggested_first_action}",
                f"- Similar failures: {', '.join(failure.similar_failures) or 'None'}",
                "",
            ]
        )
    return "\n".join(lines)


def write_report(report: TriageReport, output_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable and Markdown triage artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "triage-report.json"
    markdown_path = output_dir / "triage-report.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def build_parser() -> argparse.ArgumentParser:
    """Build a stable CLI shared by local scripts and CI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "junit_positional",
        type=Path,
        nargs="?",
        help="JUnit XML file or directory produced by pytest",
    )
    parser.add_argument(
        "--junit",
        dest="junit_option",
        type=Path,
        help="JUnit XML file or directory produced by pytest",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        action="append",
        default=[],
        help="Optional console or HTTP JSON evidence (repeatable)",
    )
    parser.add_argument(
        "--console",
        type=Path,
        action="append",
        default=[],
        help="Browser console evidence file or directory (repeatable)",
    )
    parser.add_argument(
        "--http",
        type=Path,
        action="append",
        default=[],
        help="HTTP failure evidence file or directory (repeatable)",
    )
    parser.add_argument(
        "--output-dir",
        "--output",
        dest="output_dir",
        type=Path,
        default=Path("artifacts/triage"),
    )
    return parser


def main() -> None:
    """CLI entry point."""
    arguments = build_parser().parse_args()
    junit_path = arguments.junit_option or arguments.junit_positional
    if junit_path is None:
        build_parser().error(
            "a JUnit file or directory is required via --junit or positional input"
        )
    evidence_paths = [*arguments.evidence, *arguments.console, *arguments.http]
    try:
        report = generate_report(junit_path, evidence_paths=evidence_paths)
        json_path, markdown_path = write_report(report, arguments.output_dir)
    except (OSError, ET.ParseError) as error:
        sys.stderr.write(f"Failure triage could not read its inputs: {error}\n")
        raise SystemExit(2) from error
    sys.stdout.write(f"Wrote {json_path} and {markdown_path}\n")


if __name__ == "__main__":
    main()
