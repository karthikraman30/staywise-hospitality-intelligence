#!/usr/bin/env python3
"""Serve the source-backed StayWise interview dashboard without dependencies."""

from __future__ import annotations

import csv
import argparse
import json
import math
from collections import defaultdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
FACTS_PATH = ROOT / "data" / "processed" / "fact_bookings.csv"
INVENTORY_PATH = ROOT / "data" / "processed" / "fact_daily_inventory.csv"
RISK_PATH = ROOT / "outputs" / "cancellation_risk_segments.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def number(value: str | float | int | None) -> float:
    return float(value or 0)


class DashboardStore:
    def __init__(self) -> None:
        self.facts = read_csv(FACTS_PATH)
        self.inventory = read_csv(INVENTORY_PATH)
        self.risk = read_csv(RISK_PATH)
        self.property_names = {"P001": "StayWise Resort Algarve", "P002": "StayWise City Lisbon"}

    def filters(self) -> dict[str, Any]:
        return {
            "properties": [{"id": key, "name": value} for key, value in self.property_names.items()],
            "months": sorted({row["arrival_year_month"] for row in self.facts}),
            "channels": sorted({row["distribution_channel"] for row in self.facts}),
            "segments": sorted({row["market_segment"] for row in self.facts}),
        }

    @staticmethod
    def selected(params: dict[str, list[str]], key: str) -> str:
        value = params.get(key, [""])[0]
        return "" if value in ("", "All") else value

    def filtered_facts(self, params: dict[str, list[str]]) -> list[dict[str, str]]:
        property_id = self.selected(params, "property")
        month = self.selected(params, "month")
        channel = self.selected(params, "channel")
        segment = self.selected(params, "segment")
        return [
            row for row in self.facts
            if (not property_id or row["property_id"] == property_id)
            and (not month or row["arrival_year_month"] == month)
            and (not channel or row["distribution_channel"] == channel)
            and (not segment or row["market_segment"] == segment)
        ]

    def available_nights(self, params: dict[str, list[str]]) -> int:
        property_id = self.selected(params, "property")
        month = self.selected(params, "month")
        return sum(
            int(row["available_room_nights"])
            for row in self.inventory
            if (not property_id or row["property_id"] == property_id)
            and (not month or row["date"].startswith(month))
        )

    def summary(self, params: dict[str, list[str]]) -> dict[str, float | int]:
        rows = self.filtered_facts(params)
        values = defaultdict(float)
        for row in rows:
            values["bookings"] += 1
            values["cancellations"] += number(row["is_canceled"])
            for field in ("potential_revenue", "realized_revenue", "lost_revenue", "commission_cost", "net_revenue", "room_nights_realized"):
                values[field] += number(row[field])
        available = self.available_nights(params)
        realized = values["realized_revenue"]
        room_nights = values["room_nights_realized"]
        return {
            "bookings": int(values["bookings"]),
            "cancellations": int(values["cancellations"]),
            "cancellation_rate": values["cancellations"] / values["bookings"] if values["bookings"] else 0,
            "potential_revenue": round(values["potential_revenue"], 2),
            "realized_revenue": round(realized, 2),
            "lost_revenue": round(values["lost_revenue"], 2),
            "commission_cost": round(values["commission_cost"], 2),
            "net_revenue": round(values["net_revenue"], 2),
            "available_room_nights": available,
            "occupancy_rate": room_nights / available if available else 0,
            "adr": realized / room_nights if room_nights else 0,
            "revpar": realized / available if available else 0,
            "net_revpar": values["net_revenue"] / available if available else 0,
        }

    def monthly(self, params: dict[str, list[str]]) -> list[dict[str, float | int | str]]:
        rows = self.filtered_facts(params)
        property_id = self.selected(params, "property")
        grouped: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for row in rows:
            bucket = grouped[row["arrival_year_month"]]
            bucket["bookings"] += 1
            bucket["realized_revenue"] += number(row["realized_revenue"])
            bucket["lost_revenue"] += number(row["lost_revenue"])
        result = []
        for month, values in sorted(grouped.items()):
            available = sum(
                int(row["available_room_nights"])
                for row in self.inventory
                if row["date"].startswith(month) and (not property_id or row["property_id"] == property_id)
            )
            result.append({"month": month, "bookings": int(values["bookings"]), "realized_revenue": round(values["realized_revenue"], 2), "lost_revenue": round(values["lost_revenue"], 2), "available_room_nights": available})
        return result

    def drivers(self, params: dict[str, list[str]]) -> list[dict[str, float | int | str]]:
        groups: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        labels = {
            "lead_time_band": "Lead time", "distribution_channel": "Channel",
            "market_segment": "Market segment", "deposit_type": "Deposit type",
        }
        for row in self.filtered_facts(params):
            for field, label in labels.items():
                bucket = groups[(label, row[field])]
                bucket["bookings"] += 1
                bucket["cancellations"] += number(row["is_canceled"])
                bucket["lost_revenue"] += number(row["lost_revenue"])
        result = []
        for (driver_type, driver_value), values in groups.items():
            result.append({
                "driver_type": driver_type, "driver_value": driver_value, "bookings": int(values["bookings"]),
                "cancellation_rate": values["cancellations"] / values["bookings"] if values["bookings"] else 0,
                "lost_revenue": round(values["lost_revenue"], 2),
            })
        return sorted(result, key=lambda row: (str(row["driver_type"]), -float(row["cancellation_rate"])))

    def channels(self, params: dict[str, list[str]]) -> list[dict[str, float | int | str]]:
        groups: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for row in self.filtered_facts(params):
            bucket = groups[row["distribution_channel"]]
            bucket["bookings"] += 1
            bucket["cancellations"] += number(row["is_canceled"])
            bucket["realized_revenue"] += number(row["realized_revenue"])
            bucket["commission_cost"] += number(row["commission_cost"])
            bucket["net_revenue"] += number(row["net_revenue"])
        return sorted([
            {"channel": channel, "bookings": int(values["bookings"]), "cancellation_rate": values["cancellations"] / values["bookings"] if values["bookings"] else 0,
             "realized_revenue": round(values["realized_revenue"], 2), "commission_cost": round(values["commission_cost"], 2), "net_revenue": round(values["net_revenue"], 2)}
            for channel, values in groups.items()
        ], key=lambda row: -float(row["net_revenue"]))

    def opportunities(self, params: dict[str, list[str]]) -> list[dict[str, float | int | str]]:
        rows = self.filtered_facts(params)
        base_rate = sum(number(row["is_canceled"]) for row in rows) / len(rows) if rows else 0
        groups: dict[tuple[str, str, str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for row in rows:
            key = (row["property_id"], row["market_segment"], row["distribution_channel"], row["lead_time_band"], row["deposit_type"])
            bucket = groups[key]
            bucket["bookings"] += 1
            bucket["cancellations"] += number(row["is_canceled"])
            bucket["lost_revenue"] += number(row["lost_revenue"])
        result = []
        for (property_id, segment, channel, lead_band, deposit_type), values in groups.items():
            if values["bookings"] < 120:
                continue
            rate = values["cancellations"] / values["bookings"]
            reduction = min(0.35, max(0.06, max(rate - base_rate, 0) * 0.65))
            result.append({
                "property_id": property_id, "property_name": self.property_names[property_id], "market_segment": segment,
                "distribution_channel": channel, "lead_time_band": lead_band, "deposit_type": deposit_type,
                "bookings": int(values["bookings"]), "cancellation_rate": rate, "lost_revenue": round(values["lost_revenue"], 2),
                "estimated_recoverable_revenue": round(values["lost_revenue"] * reduction, 2),
                "recommended_intervention": "Pilot staged deposit or reconfirmation workflow" if lead_band in ("91-180 days", "181+ days") else "Review channel and cancellation policy",
            })
        ranked = sorted(result, key=lambda item: -float(item["estimated_recoverable_revenue"]))
        for rank, row in enumerate(ranked, start=1):
            row["priority_rank"] = rank
        return ranked[:15]

    def scenario(self, params: dict[str, list[str]]) -> dict[str, float]:
        summary = self.summary(params)
        def assumption(name: str) -> float:
            try:
                return min(max(float(params.get(name, ["0"])[0]), 0), 0.5)
            except ValueError:
                return 0
        cancellation = assumption("cancellation_reduction")
        adr = assumption("adr_uplift")
        occupancy = assumption("occupancy_uplift")
        channel_mix = assumption("channel_mix")
        recovered = summary["lost_revenue"] * cancellation
        adr_impact = summary["realized_revenue"] * adr
        occupancy_impact = summary["realized_revenue"] * occupancy
        channel_savings = summary["commission_cost"] * channel_mix
        total = recovered + adr_impact + occupancy_impact + channel_savings
        return {"recovered_revenue": round(recovered, 2), "adr_impact": round(adr_impact, 2), "occupancy_impact": round(occupancy_impact, 2), "channel_cost_savings": round(channel_savings, 2), "total_incremental_revenue": round(total, 2), "new_revenue": round(summary["realized_revenue"] + total, 2), "revenue_lift": total / summary["realized_revenue"] if summary["realized_revenue"] else 0}


STORE = DashboardStore()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(DASHBOARD), **kwargs)

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return super().do_GET()
        params = parse_qs(parsed.query)
        routes = {
            "/api/filters": lambda: STORE.filters(), "/api/summary": lambda: STORE.summary(params),
            "/api/monthly": lambda: STORE.monthly(params), "/api/drivers": lambda: STORE.drivers(params),
            "/api/channels": lambda: STORE.channels(params), "/api/opportunities": lambda: STORE.opportunities(params),
            "/api/risk": lambda: STORE.risk, "/api/scenario": lambda: STORE.scenario(params),
        }
        route = routes.get(parsed.path)
        if route is None:
            return self.send_json({"error": "Unknown API route"}, 404)
        try:
            self.send_json(route())
        except (KeyError, ValueError, ZeroDivisionError) as exc:
            self.send_json({"error": str(exc)}, 400)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve the StayWise local dashboard.")
    parser.add_argument("--port", type=int, default=8000, help="Local HTTP port (default: 8000).")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"StayWise Decision Console: http://127.0.0.1:{args.port}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
