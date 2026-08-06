from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# ShiftBridge is a client-rendered Vite SPA. It does not enable React Router RSC mode,
# server actions, or any React Router server runtime, so this advisory's vulnerable
# execution path is absent. Unknown high/critical advisories still fail the gate.
ALLOWED_ADVISORIES = {
    "GHSA-qwww-vcr4-c8h2": (
        "React Router RSC/server-action CSRF; not reachable in this BrowserRouter-only SPA"
    ),
}
BLOCKING_SEVERITIES = {"high", "critical"}


def advisory_id(url: str) -> str:
    return url.rstrip("/").rsplit("/", maxsplit=1)[-1]


def blocking_advisories(payload: dict[str, Any]) -> dict[str, str]:
    findings: dict[str, str] = {}
    vulnerabilities = payload.get("vulnerabilities", {})
    if not isinstance(vulnerabilities, dict):
        return {"malformed-audit": "npm audit output has no vulnerability mapping"}
    for vulnerability in vulnerabilities.values():
        if not isinstance(vulnerability, dict):
            continue
        via = vulnerability.get("via", [])
        if not isinstance(via, list):
            continue
        for entry in via:
            if not isinstance(entry, dict):
                continue
            severity = str(entry.get("severity", "")).lower()
            if severity not in BLOCKING_SEVERITIES:
                continue
            url = str(entry.get("url", ""))
            identifier = advisory_id(url) if url else "unknown-advisory"
            findings[identifier] = str(entry.get("title", identifier))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail on unknown high/critical npm advisories.")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    payload: dict[str, Any] = json.loads(args.report.read_text(encoding="utf-8"))
    findings = blocking_advisories(payload)
    unknown = {
        identifier: title
        for identifier, title in findings.items()
        if identifier not in ALLOWED_ADVISORIES
    }
    for identifier in sorted(findings):
        if identifier in ALLOWED_ADVISORIES:
            print(f"Reviewed exception {identifier}: {ALLOWED_ADVISORIES[identifier]}")
        else:
            print(f"Blocking advisory {identifier}: {findings[identifier]}")
    if unknown:
        return 1
    print("No unreviewed high or critical npm advisories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
