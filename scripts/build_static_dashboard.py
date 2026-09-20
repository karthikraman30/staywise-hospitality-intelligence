#!/usr/bin/env python3
"""Pre-aggregate the booking fact table so the dashboard can run without a server.

Writes dashboard/data.js with bookings grouped by every filter/driver dimension the
dashboard uses (property, month, channel, segment, lead-time band, deposit type).
Every metric the dashboard shows is a sum or ratio over these cells, so the static
page reproduces scripts/serve_dashboard.py exactly.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "data" / "processed" / "fact_bookings.csv"
INVENTORY_PATH = ROOT / "data" / "processed" / "fact_daily_inventory.csv"
RISK_PATH = ROOT / "outputs" / "cancellation_risk_segments.csv"
OUT_PATH = ROOT / "dashboard" / "data.js"

KEY = ("property_id", "arrival_year_month", "distribution_channel", "market_segment", "lead_time_band", "deposit_type")
SUMS = ("potential_revenue", "realized_revenue", "lost_revenue", "commission_cost", "net_revenue", "room_nights_realized")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    cells: dict[tuple[str, ...], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in read_csv(FACTS_PATH):
        cell = cells[tuple(row[k] for k in KEY)]
        cell["bookings"] += 1
        cell["cancellations"] += int(row["is_canceled"])
        for field in SUMS:
            cell[field] += float(row[field])

    inventory: dict[tuple[str, str], int] = defaultdict(int)
    for row in read_csv(INVENTORY_PATH):
        inventory[(row["property_id"], row["date"][:7])] += int(row["available_room_nights"])

    payload = {
        "generated_from": "data/processed/fact_bookings.csv",
        "property_names": {"P001": "StayWise Resort Algarve", "P002": "StayWise City Lisbon"},
        "columns": list(KEY) + ["bookings", "cancellations"] + list(SUMS),
        "cells": [
            list(key) + [int(c["bookings"]), int(c["cancellations"])] + [round(c[f], 2) for f in SUMS]
            for key, c in sorted(cells.items())
        ],
        "inventory": [[p, m, n] for (p, m), n in sorted(inventory.items())],
        "risk": [
            {k: (float(v) if k != "risk_band" else v) for k, v in row.items()}
            for row in read_csv(RISK_PATH)
        ],
    }
    OUT_PATH.write_text("window.STAYWISE_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {len(payload['cells']):,} cells, {OUT_PATH.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
