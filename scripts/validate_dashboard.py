#!/usr/bin/env python3
"""Smoke-test the StayWise local dashboard API against validated outputs."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"


def read_json(path: str) -> object:
    with urlopen(f"{BASE_URL}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    server = subprocess.Popen(
        [sys.executable, "scripts/serve_dashboard.py", "--port", str(PORT)], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
    )
    errors: list[str] = []
    try:
        for _ in range(30):
            try:
                filters = read_json("/api/filters")
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Dashboard server did not start")

        if not isinstance(filters, dict) or len(filters.get("months", [])) < 20:
            errors.append("Dashboard filters are incomplete")

        summary = read_json("/api/summary")
        with (ROOT / "outputs/executive_summary.csv").open(newline="", encoding="utf-8") as fh:
            expected = next(csv.DictReader(fh))
        for field in ("bookings", "realized_revenue", "lost_revenue", "net_revenue"):
            if abs(float(summary[field]) - float(expected[field])) > 1:
                errors.append(f"Dashboard {field} does not reconcile to executive_summary.csv")

        opportunities = read_json("/api/opportunities")
        if not opportunities or opportunities[0]["priority_rank"] != 1:
            errors.append("Dashboard opportunity ranking is missing rank 1")
        elif opportunities[0]["property_id"] != "P001" or opportunities[0]["lead_time_band"] != "181+ days":
            errors.append("Dashboard top opportunity does not match the portfolio baseline")

        filtered = read_json("/api/summary?property=P001&channel=TA%2FTO")
        if filtered["bookings"] <= 0 or filtered["bookings"] >= summary["bookings"]:
            errors.append("Dashboard property/channel filter did not narrow the population")

        scenario = read_json("/api/scenario?cancellation_reduction=0.05&adr_uplift=0.03&occupancy_uplift=0.02&channel_mix=0.04")
        if scenario["total_incremental_revenue"] <= 0 or scenario["new_revenue"] <= summary["realized_revenue"]:
            errors.append("Dashboard scenario calculation is not producing an incremental impact")
    except Exception as exc:
        errors.append(f"Dashboard validation could not run: {exc}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    if errors:
        print("Dashboard validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Dashboard validation passed: API, filters, scenario controls, and KPI reconciliation are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
