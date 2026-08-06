from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_TARGETS = (
    ROOT / ".coverage",
    ROOT / ".hypothesis",
    ROOT / ".mypy_cache",
    ROOT / ".pytest_cache",
    ROOT / ".ruff_cache",
    ROOT / "artifacts",
    ROOT / "htmlcov",
    ROOT / "apps" / "web" / "dist",
)


def main() -> None:
    for target in SAFE_TARGETS:
        resolved = target.resolve()
        if ROOT not in resolved.parents:
            raise RuntimeError(f"Refusing to clean outside repository: {resolved}")
        if resolved.is_dir():
            shutil.rmtree(resolved)
        elif resolved.exists():
            resolved.unlink()
    print("Removed generated ShiftBridge artifacts.")


if __name__ == "__main__":
    main()
