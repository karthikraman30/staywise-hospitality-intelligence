#!/usr/bin/env python3
"""Reconcile the PostgreSQL implementation (local server or Docker) with StayWise outputs.

Set STAYWISE_PSQL_MODE=local to use the psql on PATH against $PGDATABASE (default: staywise).
Otherwise the Docker container started by `make db-up` is used.
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSQL_FLAGS = ["-At", "-F", ",", "-v", "ON_ERROR_STOP=1", "-c"]
if os.environ.get("STAYWISE_PSQL_MODE", "docker") == "local":
    PSQL = ["psql", "-d", os.environ.get("PGDATABASE", "staywise")] + PSQL_FLAGS
else:
    PSQL = ["docker", "exec", "-i", "-w", "/workspace", "staywise-postgres", "psql", "-U", "staywise", "-d", "staywise"] + PSQL_FLAGS


def query(sql: str) -> list[list[str]]:
    result = subprocess.run(PSQL + [sql], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return [line.split(",") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    errors: list[str] = []
    try:
        row_count = query("SELECT COUNT(*) FROM staywise.fact_bookings;")
        if row_count != [["119390"]]:
            errors.append(f"Expected 119390 bookings in PostgreSQL; found {row_count}")

        exceptions = query(
            "SELECT COUNT(*) FROM staywise.fact_bookings "
            "WHERE potential_revenue < 0 OR realized_revenue < 0 OR lost_revenue < 0 "
            "OR ABS(potential_revenue - realized_revenue - lost_revenue) > 0.011;"
        )
        if exceptions != [["0"]]:
            errors.append(f"Revenue reconciliation exceptions in PostgreSQL: {exceptions}")

        with (ROOT / "outputs/executive_summary.csv").open(newline="", encoding="utf-8") as fh:
            summary = next(csv.DictReader(fh))
        kpis = query(
            "SELECT ROUND(realized_revenue, 2), ROUND(lost_revenue, 2), ROUND(net_revenue, 2) "
            "FROM staywise.vw_executive_kpis;"
        )[0]
        expected = [summary["realized_revenue"], summary["lost_revenue"], summary["net_revenue"]]
        for name, actual, expected_value in zip(("realized revenue", "lost revenue", "net revenue"), kpis, expected):
            if abs(float(actual) - float(expected_value)) > 1:
                errors.append(f"PostgreSQL {name} does not reconcile: {actual} vs {expected_value}")

        top = query("SELECT priority_rank, property_id, market_segment, distribution_channel, lead_time_band FROM staywise.vw_opportunity_rankings LIMIT 1;")
        if top != [["1", "P001", "Online TA", "TA/TO", "181+ days"]]:
            errors.append(f"Unexpected top PostgreSQL opportunity: {top}")
    except (RuntimeError, IndexError, OSError) as exc:
        errors.append(f"PostgreSQL validation could not run: {exc}")

    if errors:
        print("Database validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Database validation passed: schema, KPI reconciliation, and top opportunity match generated outputs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
