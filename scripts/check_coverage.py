from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TypedDict


class Totals(TypedDict):
    covered_lines: int
    num_statements: int
    covered_branches: int
    num_branches: int


class CoveragePayload(TypedDict):
    totals: Totals


def percentage(covered: int, total: int) -> float:
    return 100.0 if total == 0 else (covered / total) * 100


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce separate line and branch coverage gates.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--line", type=float, required=True)
    parser.add_argument("--branch", type=float, required=True)
    args = parser.parse_args()

    payload: CoveragePayload = json.loads(args.report.read_text(encoding="utf-8"))
    totals = payload["totals"]
    line = percentage(totals["covered_lines"], totals["num_statements"])
    branch = percentage(totals["covered_branches"], totals["num_branches"])
    print(f"Line coverage: {line:.2f}% (required {args.line:.2f}%)")
    print(f"Branch coverage: {branch:.2f}% (required {args.branch:.2f}%)")
    return 0 if line >= args.line and branch >= args.branch else 1


if __name__ == "__main__":
    raise SystemExit(main())
