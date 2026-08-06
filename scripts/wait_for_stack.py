from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


@dataclass(frozen=True)
class Probe:
    name: str
    url: str


PROBES = (
    Probe("API liveness", "http://localhost:8000/health/live"),
    Probe("API readiness", "http://localhost:8000/health/ready"),
    Probe("web", "http://localhost:4173/health"),
)


def is_healthy(probe: Probe) -> bool:
    try:
        with urlopen(probe.url, timeout=2) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            if response.status != 200:
                return False
            if "api" in probe.name.lower():
                payload = json.loads(body)
                return payload.get("status") in {"ok", "ready", "alive"}
            return True
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return False


def main() -> int:
    deadline = time.monotonic() + 90
    pending = list(PROBES)
    while pending and time.monotonic() < deadline:
        pending = [probe for probe in pending if not is_healthy(probe)]
        if pending:
            time.sleep(1)
    if pending:
        names = ", ".join(probe.name for probe in pending)
        print(f"Timed out waiting for: {names}", file=sys.stderr)
        return 1
    print("ShiftBridge API and web services are healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
