#!/usr/bin/env python3
"""Build the StayWise portfolio project with only the Python standard library."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import random
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
RAW_URL = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-02-11/hotels.csv"
RAW_PATH = ROOT / "data" / "raw" / "hotels.csv"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
EXCEL = ROOT / "excel"
DOCS = ROOT / "docs"
POWERBI = ROOT / "powerbi"
NOTEBOOKS = ROOT / "notebooks"

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

PROPERTY_META = {
    "Resort Hotel": {
        "property_id": "P001",
        "property_name": "StayWise Resort Algarve",
        "property_type": "Resort",
        "city": "Algarve",
        "country": "Portugal",
        "room_count": 280,
        "target_adr": 115.0,
        "target_occupancy": 0.72,
    },
    "City Hotel": {
        "property_id": "P002",
        "property_name": "StayWise City Lisbon",
        "property_type": "City",
        "city": "Lisbon",
        "country": "Portugal",
        "room_count": 450,
        "target_adr": 102.0,
        "target_occupancy": 0.78,
    },
}

CHANNEL_META = {
    "Direct": ("Direct", "Owned", 0.02),
    "Corporate": ("Corporate", "Negotiated", 0.03),
    "GDS": ("GDS", "Managed intermediary", 0.10),
    "TA/TO": ("Travel Agent / Tour Operator", "OTA / wholesale", 0.18),
    "Undefined": ("Undefined", "Unknown", 0.12),
}


def ensure_dirs() -> None:
    for path in [RAW_PATH.parent, PROCESSED, OUTPUTS, OUTPUTS / "charts", EXCEL, DOCS, POWERBI, NOTEBOOKS]:
        path.mkdir(parents=True, exist_ok=True)


def download_raw(force: bool = False) -> None:
    if RAW_PATH.exists() and not force:
        return
    print(f"Downloading raw dataset to {RAW_PATH}")
    with urllib.request.urlopen(RAW_URL, timeout=60) as response, RAW_PATH.open("wb") as fh:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)


def as_int(value: str | None, default: int = 0) -> int:
    try:
        if value in (None, "", "NA", "NULL"):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: str | None, default: float = 0.0) -> float:
    try:
        if value in (None, "", "NA", "NULL"):
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def pct(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent(value: float) -> str:
    return f"{value:.1%}"


def lead_band(days: int) -> str:
    if days <= 7:
        return "0-7 days"
    if days <= 30:
        return "8-30 days"
    if days <= 90:
        return "31-90 days"
    if days <= 180:
        return "91-180 days"
    return "181+ days"


def stay_band(nights: int) -> str:
    if nights <= 1:
        return "1 night"
    if nights <= 3:
        return "2-3 nights"
    if nights <= 7:
        return "4-7 nights"
    return "8+ nights"


def special_request_band(count: int) -> str:
    if count == 0:
        return "No requests"
    if count == 1:
        return "1 request"
    return "2+ requests"


def previous_cancel_band(count: int) -> str:
    if count == 0:
        return "No previous cancellations"
    if count == 1:
        return "1 previous cancellation"
    return "2+ previous cancellations"


def cancellation_recovery_rate(deposit_type: str) -> float:
    if deposit_type == "Non Refund":
        return 0.85
    if deposit_type == "Refundable":
        return 0.20
    return 0.0


def clean_id(prefix: str, index: int) -> str:
    return f"{prefix}{index:03d}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_raw_rows() -> list[dict]:
    with RAW_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_model(raw_rows: list[dict]) -> dict:
    channel_ids = {name: clean_id("CH", i + 1) for i, name in enumerate(sorted(CHANNEL_META))}
    market_values = sorted({r.get("market_segment") or "Undefined" for r in raw_rows})
    customer_values = sorted({r.get("customer_type") or "Undefined" for r in raw_rows})
    room_values = sorted({r.get("reserved_room_type") or "Undefined" for r in raw_rows})
    country_values = sorted({r.get("country") or "Unknown" for r in raw_rows})

    market_ids = {name: clean_id("MS", i + 1) for i, name in enumerate(market_values)}
    customer_ids = {name: clean_id("CT", i + 1) for i, name in enumerate(customer_values)}
    room_ids = {name: clean_id("RT", i + 1) for i, name in enumerate(room_values)}
    country_ids = {name: clean_id("CO", i + 1) for i, name in enumerate(country_values)}

    facts: list[dict] = []
    dates: set[dt.date] = set()

    for index, row in enumerate(raw_rows, start=1):
        hotel = row.get("hotel") or "City Hotel"
        meta = PROPERTY_META.get(hotel, PROPERTY_META["City Hotel"])
        year = as_int(row.get("arrival_date_year"), 2017)
        month = MONTHS.get(row.get("arrival_date_month"), 1)
        day = as_int(row.get("arrival_date_day_of_month"), 1)
        try:
            arrival_date = dt.date(year, month, day)
        except ValueError:
            continue

        weekend_nights = as_int(row.get("stays_in_weekend_nights"))
        week_nights = as_int(row.get("stays_in_week_nights"))
        stay_nights = max(weekend_nights + week_nights, 1)
        adr = max(as_float(row.get("adr")), 0.0)
        is_canceled = as_int(row.get("is_canceled"))
        lead_time = as_int(row.get("lead_time"))
        channel = row.get("distribution_channel") or "Undefined"
        market_segment = row.get("market_segment") or "Undefined"
        customer_type = row.get("customer_type") or "Undefined"
        room_type = row.get("reserved_room_type") or "Undefined"
        country = row.get("country") or "Unknown"
        deposit_type = row.get("deposit_type") or "Undefined"
        special_requests = as_int(row.get("total_of_special_requests"))
        previous_cancellations = as_int(row.get("previous_cancellations"))
        adults = as_int(row.get("adults"))
        children = as_int(row.get("children"))
        babies = as_int(row.get("babies"))
        guests = max(adults + children + babies, 1)
        deposit_recovery_rate = cancellation_recovery_rate(deposit_type)
        # Round at booking grain, then derive the residual so revenue reconciles exactly.
        potential_revenue = round(adr * stay_nights, 2)
        stay_revenue = 0.0 if is_canceled else potential_revenue
        cancellation_fee_revenue = round(potential_revenue * deposit_recovery_rate, 2) if is_canceled else 0.0
        realized_revenue = round(stay_revenue + cancellation_fee_revenue, 2)
        lost_revenue = round(potential_revenue - realized_revenue, 2) if is_canceled else 0.0
        commission_rate = CHANNEL_META.get(channel, CHANNEL_META["Undefined"])[2]
        commission_cost = realized_revenue * commission_rate
        net_revenue = realized_revenue - commission_cost
        room_mismatch = 1 if (row.get("assigned_room_type") or room_type) != room_type else 0

        dates.add(arrival_date)
        facts.append(
            {
                "booking_id": f"SW{index:06d}",
                "arrival_date": arrival_date.isoformat(),
                "date_id": arrival_date.strftime("%Y%m%d"),
                "arrival_year_month": arrival_date.strftime("%Y-%m"),
                "property_id": meta["property_id"],
                "channel_id": channel_ids.get(channel, channel_ids["Undefined"]),
                "market_segment_id": market_ids[market_segment],
                "customer_type_id": customer_ids[customer_type],
                "room_type_id": room_ids[room_type],
                "country_id": country_ids[country],
                "hotel_source": hotel,
                "distribution_channel": channel,
                "market_segment": market_segment,
                "customer_type": customer_type,
                "reserved_room_type": room_type,
                "deposit_type": deposit_type,
                "reservation_status": row.get("reservation_status") or "Undefined",
                "lead_time": lead_time,
                "lead_time_band": lead_band(lead_time),
                "stay_nights": stay_nights,
                "stay_band": stay_band(stay_nights),
                "guests": guests,
                "adr": round(adr, 2),
                "is_canceled": is_canceled,
                "potential_revenue": potential_revenue,
                "stay_revenue": stay_revenue,
                "realized_revenue": realized_revenue,
                "lost_revenue": lost_revenue,
                "deposit_recovery_rate": deposit_recovery_rate,
                "cancellation_fee_revenue": cancellation_fee_revenue,
                "commission_rate": commission_rate,
                "commission_cost": round(commission_cost, 2),
                "net_revenue": round(net_revenue, 2),
                "room_nights_booked": stay_nights,
                "room_nights_realized": 0 if is_canceled else stay_nights,
                "previous_cancellations": previous_cancellations,
                "previous_cancel_band": previous_cancel_band(previous_cancellations),
                "total_special_requests": special_requests,
                "special_request_band": special_request_band(special_requests),
                "booking_changes": as_int(row.get("booking_changes")),
                "days_in_waiting_list": as_int(row.get("days_in_waiting_list")),
                "required_car_parking_spaces": as_int(row.get("required_car_parking_spaces")),
                "room_mismatch_flag": room_mismatch,
            }
        )

    dim_date = [
        {
            "date_id": d.strftime("%Y%m%d"),
            "date": d.isoformat(),
            "year": d.year,
            "month_number": d.month,
            "month_name": d.strftime("%B"),
            "quarter": f"Q{((d.month - 1) // 3) + 1}",
            "year_month": d.strftime("%Y-%m"),
            "day_of_week": d.strftime("%A"),
            "is_weekend": 1 if d.weekday() >= 5 else 0,
        }
        for d in sorted(dates)
    ]

    dim_property = [
        {
            "property_id": meta["property_id"],
            "property_name": meta["property_name"],
            "property_type": meta["property_type"],
            "city": meta["city"],
            "country": meta["country"],
            "room_count": meta["room_count"],
            "target_adr": meta["target_adr"],
            "target_occupancy": meta["target_occupancy"],
        }
        for _, meta in sorted(PROPERTY_META.items(), key=lambda item: item[1]["property_id"])
    ]

    dim_channel = [
        {
            "channel_id": channel_ids[channel],
            "distribution_channel": channel,
            "channel_name": CHANNEL_META[channel][0],
            "channel_group": CHANNEL_META[channel][1],
            "commission_rate": CHANNEL_META[channel][2],
        }
        for channel in sorted(channel_ids)
    ]

    dim_market_segment = [
        {"market_segment_id": market_ids[name], "market_segment": name}
        for name in sorted(market_ids, key=lambda k: market_ids[k])
    ]
    dim_customer = [
        {"customer_type_id": customer_ids[name], "customer_type": name}
        for name in sorted(customer_ids, key=lambda k: customer_ids[k])
    ]
    dim_room_type = [
        {"room_type_id": room_ids[name], "room_type": name}
        for name in sorted(room_ids, key=lambda k: room_ids[k])
    ]
    dim_country = [
        {"country_id": country_ids[name], "country_code": name, "country_name": "Unknown" if name == "Unknown" else name}
        for name in sorted(country_ids, key=lambda k: country_ids[k])
    ]

    min_date, max_date = min(dates), max(dates)
    daily_inventory: list[dict] = []
    current = min_date
    while current <= max_date:
        for meta in PROPERTY_META.values():
            season_factor = 1.0
            if current.month in (6, 7, 8):
                season_factor = 0.98
            if current.month in (1, 2):
                season_factor = 1.02
            available = round(meta["room_count"] * season_factor)
            daily_inventory.append(
                {
                    "date_id": current.strftime("%Y%m%d"),
                    "date": current.isoformat(),
                    "property_id": meta["property_id"],
                    "room_count": meta["room_count"],
                    "available_room_nights": available,
                    "source_type": "synthetic_operating_capacity",
                }
            )
        current += dt.timedelta(days=1)

    monthly_targets = build_monthly_targets(min_date, max_date)
    local_events = build_local_events(min_date, max_date)
    interventions = build_interventions()

    return {
        "fact_bookings": facts,
        "dim_date": dim_date,
        "dim_property": dim_property,
        "dim_channel": dim_channel,
        "dim_market_segment": dim_market_segment,
        "dim_customer": dim_customer,
        "dim_room_type": dim_room_type,
        "dim_country": dim_country,
        "fact_daily_inventory": daily_inventory,
        "fact_monthly_targets": monthly_targets,
        "fact_local_events": local_events,
        "dim_intervention_options": interventions,
    }


def month_range(min_date: dt.date, max_date: dt.date) -> list[dt.date]:
    current = dt.date(min_date.year, min_date.month, 1)
    end = dt.date(max_date.year, max_date.month, 1)
    months = []
    while current <= end:
        months.append(current)
        if current.month == 12:
            current = dt.date(current.year + 1, 1, 1)
        else:
            current = dt.date(current.year, current.month + 1, 1)
    return months


def build_monthly_targets(min_date: dt.date, max_date: dt.date) -> list[dict]:
    rows = []
    for month_start in month_range(min_date, max_date):
        seasonal_occupancy = 0.05 if month_start.month in (6, 7, 8) else -0.03 if month_start.month in (1, 2) else 0.0
        seasonal_adr = 1.12 if month_start.month in (6, 7, 8) else 0.92 if month_start.month in (1, 2) else 1.0
        for meta in PROPERTY_META.values():
            rows.append(
                {
                    "target_id": f"TGT-{meta['property_id']}-{month_start:%Y%m}",
                    "year_month": month_start.strftime("%Y-%m"),
                    "property_id": meta["property_id"],
                    "target_occupancy": round(min(meta["target_occupancy"] + seasonal_occupancy, 0.9), 4),
                    "target_adr": round(meta["target_adr"] * seasonal_adr, 2),
                    "target_cancellation_rate": 0.28 if meta["property_type"] == "City" else 0.22,
                    "source_type": "synthetic_management_target",
                }
            )
    return rows


def build_local_events(min_date: dt.date, max_date: dt.date) -> list[dict]:
    rows = []
    for month_start in month_range(min_date, max_date):
        for meta in PROPERTY_META.values():
            base = 60 if meta["property_type"] == "City" else 45
            seasonal = 25 if month_start.month in (6, 7, 8) else 10 if month_start.month in (4, 5, 9, 10) else 0
            city_boost = 15 if meta["property_type"] == "City" and month_start.month in (3, 11) else 0
            event_index = base + seasonal + city_boost
            competitor_index = 1 + ((event_index - 60) / 500)
            rows.append(
                {
                    "event_id": f"EVT-{meta['property_id']}-{month_start:%Y%m}",
                    "year_month": month_start.strftime("%Y-%m"),
                    "property_id": meta["property_id"],
                    "local_event_intensity_index": round(event_index, 1),
                    "competitor_rate_index": round(competitor_index, 3),
                    "source_type": "synthetic_market_context",
                }
            )
    return rows


def build_interventions() -> list[dict]:
    return [
        {
            "intervention_id": "INT001",
            "intervention_name": "Early OTA cancellation deposit test",
            "primary_driver": "High-lead-time OTA cancellations",
            "owner_role": "Revenue Manager",
            "expected_kpi": "Cancellation rate",
            "implementation_effort": "Medium",
        },
        {
            "intervention_id": "INT002",
            "intervention_name": "Direct booking loyalty incentive",
            "primary_driver": "Channel profitability",
            "owner_role": "Marketing Lead",
            "expected_kpi": "Net RevPAR",
            "implementation_effort": "Medium",
        },
        {
            "intervention_id": "INT003",
            "intervention_name": "Low-request booking confirmation workflow",
            "primary_driver": "No-special-request cancellation risk",
            "owner_role": "Operations Manager",
            "expected_kpi": "Realized room nights",
            "implementation_effort": "Low",
        },
        {
            "intervention_id": "INT004",
            "intervention_name": "Shoulder-season occupancy package",
            "primary_driver": "Underutilized inventory",
            "owner_role": "General Manager",
            "expected_kpi": "Occupancy rate",
            "implementation_effort": "Medium",
        },
    ]


def export_model(model: dict) -> None:
    field_order = {
        "fact_bookings": [
            "booking_id",
            "arrival_date",
            "date_id",
            "arrival_year_month",
            "property_id",
            "channel_id",
            "market_segment_id",
            "customer_type_id",
            "room_type_id",
            "country_id",
            "hotel_source",
            "distribution_channel",
            "market_segment",
            "customer_type",
            "reserved_room_type",
            "deposit_type",
            "reservation_status",
            "lead_time",
            "lead_time_band",
            "stay_nights",
            "stay_band",
            "guests",
            "adr",
            "is_canceled",
            "potential_revenue",
            "stay_revenue",
            "realized_revenue",
            "lost_revenue",
            "deposit_recovery_rate",
            "cancellation_fee_revenue",
            "commission_rate",
            "commission_cost",
            "net_revenue",
            "room_nights_booked",
            "room_nights_realized",
            "previous_cancellations",
            "previous_cancel_band",
            "total_special_requests",
            "special_request_band",
            "booking_changes",
            "days_in_waiting_list",
            "required_car_parking_spaces",
            "room_mismatch_flag",
        ]
    }
    for name, rows in model.items():
        write_csv(PROCESSED / f"{name}.csv", rows, field_order.get(name))


def aggregate_metrics(model: dict) -> dict:
    facts = model["fact_bookings"]
    properties = {row["property_id"]: row for row in model["dim_property"]}
    inventory_by_month_property: dict[tuple[str, str], int] = defaultdict(int)
    for row in model["fact_daily_inventory"]:
        key = (row["date"][:7], row["property_id"])
        inventory_by_month_property[key] += int(row["available_room_nights"])

    monthly = defaultdict(lambda: defaultdict(float))
    channel = defaultdict(lambda: defaultdict(float))
    overall = defaultdict(float)

    for row in facts:
        prop = properties[row["property_id"]]
        key = (row["arrival_year_month"], row["property_id"])
        channel_key = (row["property_id"], row["distribution_channel"])
        for bucket in (monthly[key], channel[channel_key], overall):
            bucket["bookings"] += 1
            bucket["cancellations"] += row["is_canceled"]
            bucket["potential_revenue"] += row["potential_revenue"]
            bucket["stay_revenue"] += row["stay_revenue"]
            bucket["realized_revenue"] += row["realized_revenue"]
            bucket["lost_revenue"] += row["lost_revenue"]
            bucket["cancellation_fee_revenue"] += row["cancellation_fee_revenue"]
            bucket["commission_cost"] += row["commission_cost"]
            bucket["net_revenue"] += row["net_revenue"]
            bucket["room_nights_realized"] += row["room_nights_realized"]
            bucket["room_nights_booked"] += row["room_nights_booked"]
        channel[channel_key]["commission_rate"] = row["commission_rate"]
        channel[channel_key]["property_name"] = prop["property_name"]
        channel[channel_key]["property_type"] = prop["property_type"]

    monthly_rows = []
    for (year_month, property_id), values in sorted(monthly.items()):
        available = inventory_by_month_property[(year_month, property_id)]
        prop = properties[property_id]
        monthly_rows.append(kpi_row(values) | {
            "year_month": year_month,
            "property_id": property_id,
            "property_name": prop["property_name"],
            "property_type": prop["property_type"],
            "available_room_nights": available,
            "occupancy_rate": round(pct(values["room_nights_realized"], available), 4),
            "revpar": round(pct(values["realized_revenue"], available), 2),
            "net_revpar": round(pct(values["net_revenue"], available), 2),
        })

    channel_rows = []
    for (property_id, distribution_channel), values in sorted(channel.items()):
        prop = properties[property_id]
        channel_rows.append(kpi_row(values) | {
            "property_id": property_id,
            "property_name": prop["property_name"],
            "property_type": prop["property_type"],
            "distribution_channel": distribution_channel,
            "commission_rate": values["commission_rate"],
            "commission_cost": round(values["commission_cost"], 2),
            "net_revenue": round(values["net_revenue"], 2),
            "net_revenue_per_booking": round(pct(values["net_revenue"], values["bookings"]), 2),
        })

    all_available = sum(int(row["available_room_nights"]) for row in model["fact_daily_inventory"])
    summary = kpi_row(overall) | {
        "available_room_nights": all_available,
        "occupancy_rate": round(pct(overall["room_nights_realized"], all_available), 4),
        "revpar": round(pct(overall["realized_revenue"], all_available), 2),
        "net_revpar": round(pct(overall["net_revenue"], all_available), 2),
        "commission_cost": round(overall["commission_cost"], 2),
        "net_revenue": round(overall["net_revenue"], 2),
    }

    return {
        "monthly_kpi_summary": monthly_rows,
        "channel_profitability": channel_rows,
        "executive_summary": summary,
    }


def kpi_row(values: dict) -> dict:
    return {
        "bookings": int(values["bookings"]),
        "cancellations": int(values["cancellations"]),
        "cancellation_rate": round(pct(values["cancellations"], values["bookings"]), 4),
        "potential_revenue": round(values["potential_revenue"], 2),
        "stay_revenue": round(values["stay_revenue"], 2),
        "realized_revenue": round(values["realized_revenue"], 2),
        "lost_revenue": round(values["lost_revenue"], 2),
        "cancellation_fee_revenue": round(values["cancellation_fee_revenue"], 2),
        "room_nights_realized": int(values["room_nights_realized"]),
        "room_nights_booked": int(values["room_nights_booked"]),
        "adr": round(pct(values["realized_revenue"], values["room_nights_realized"]), 2),
    }


def driver_analysis(facts: list[dict]) -> list[dict]:
    driver_specs = [
        ("Lead Time Band", "lead_time_band"),
        ("Distribution Channel", "distribution_channel"),
        ("Market Segment", "market_segment"),
        ("Customer Type", "customer_type"),
        ("Deposit Type", "deposit_type"),
        ("Special Requests", "special_request_band"),
        ("Previous Cancellations", "previous_cancel_band"),
        ("Stay Length", "stay_band"),
    ]
    total_cancel_rate = pct(sum(r["is_canceled"] for r in facts), len(facts))
    rows = []
    for driver_name, field in driver_specs:
        groups = defaultdict(lambda: defaultdict(float))
        for row in facts:
            key = row[field]
            groups[key]["bookings"] += 1
            groups[key]["cancellations"] += row["is_canceled"]
            groups[key]["lost_revenue"] += row["lost_revenue"]
            groups[key]["realized_revenue"] += row["realized_revenue"]
        for value, metrics in groups.items():
            cancel_rate = pct(metrics["cancellations"], metrics["bookings"])
            rows.append(
                {
                    "driver_type": driver_name,
                    "driver_value": value,
                    "bookings": int(metrics["bookings"]),
                    "cancellations": int(metrics["cancellations"]),
                    "cancellation_rate": round(cancel_rate, 4),
                    "cancellation_rate_lift_vs_average": round(cancel_rate - total_cancel_rate, 4),
                    "lost_revenue": round(metrics["lost_revenue"], 2),
                    "realized_revenue": round(metrics["realized_revenue"], 2),
                }
            )
    rows.sort(key=lambda r: (r["driver_type"], -r["lost_revenue"]))
    return rows


def opportunity_analysis(facts: list[dict]) -> list[dict]:
    groups = defaultdict(lambda: defaultdict(float))
    for row in facts:
        key = (
            row["property_id"],
            row["hotel_source"],
            row["market_segment"],
            row["distribution_channel"],
            row["lead_time_band"],
            row["deposit_type"],
        )
        groups[key]["bookings"] += 1
        groups[key]["cancellations"] += row["is_canceled"]
        groups[key]["lost_revenue"] += row["lost_revenue"]
        groups[key]["realized_revenue"] += row["realized_revenue"]
        groups[key]["commission_cost"] += row["commission_cost"]
        groups[key]["room_nights_realized"] += row["room_nights_realized"]

    avg_cancel_rate = pct(sum(r["is_canceled"] for r in facts), len(facts))
    rows = []
    for key, metrics in groups.items():
        if metrics["bookings"] < 120:
            continue
        cancel_rate = pct(metrics["cancellations"], metrics["bookings"])
        excess_cancel_rate = max(cancel_rate - avg_cancel_rate, 0.0)
        achievable_reduction = min(0.35, max(0.06, excess_cancel_rate * 0.65))
        recoverable_revenue = metrics["lost_revenue"] * achievable_reduction
        property_id, hotel_source, segment, channel, lead, deposit = key
        action = recommended_action(segment, channel, lead, deposit, cancel_rate)
        rows.append(
            {
                "opportunity_id": f"OPP{len(rows) + 1:03d}",
                "property_id": property_id,
                "property_source": hotel_source,
                "market_segment": segment,
                "distribution_channel": channel,
                "lead_time_band": lead,
                "deposit_type": deposit,
                "bookings": int(metrics["bookings"]),
                "cancellations": int(metrics["cancellations"]),
                "cancellation_rate": round(cancel_rate, 4),
                "lost_revenue": round(metrics["lost_revenue"], 2),
                "realized_revenue": round(metrics["realized_revenue"], 2),
                "commission_cost": round(metrics["commission_cost"], 2),
                "achievable_cancellation_reduction": round(achievable_reduction, 4),
                "estimated_recoverable_revenue": round(recoverable_revenue, 2),
                "recommended_intervention": action,
                "priority_score": round((recoverable_revenue / 1000) + (cancel_rate * 25) + (metrics["bookings"] / 1000), 2),
            }
        )
    rows.sort(key=lambda r: r["priority_score"], reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["priority_rank"] = rank
    return rows


def recommended_action(segment: str, channel: str, lead: str, deposit: str, cancel_rate: float) -> str:
    if deposit == "Non Refund":
        return "Create resale and capacity-recapture workflow for canceled non-refundable inventory"
    if channel == "TA/TO" and lead in ("91-180 days", "181+ days"):
        return "Pilot staged deposit or reconfirmation workflow for high-lead OTA bookings"
    if segment == "Online TA":
        return "Shift demand toward direct booking offer and loyalty capture"
    if deposit == "No Deposit" and cancel_rate > 0.35:
        return "Test flexible deposit rules for high-risk no-deposit bookings"
    if lead in ("0-7 days", "8-30 days"):
        return "Use targeted pre-arrival confirmation and upsell messaging"
    return "Review pricing, cancellation policy, and capacity allocation for segment"


def risk_model(facts: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    features = [
        ("lead_time_band", "Lead time"),
        ("distribution_channel", "Channel"),
        ("market_segment", "Market segment"),
        ("customer_type", "Customer type"),
        ("deposit_type", "Deposit type"),
        ("special_request_band", "Special requests"),
        ("previous_cancel_band", "Previous cancellations"),
    ]
    base_rate = pct(sum(r["is_canceled"] for r in facts), len(facts))
    base_logit = logit(base_rate)
    feature_rates = {}
    importance_rows = []

    for field, label in features:
        groups = defaultdict(lambda: [0, 0])
        for row in facts:
            groups[row[field]][0] += 1
            groups[row[field]][1] += row["is_canceled"]
        weighted_gap = 0.0
        feature_rates[field] = {}
        for value, (bookings, cancels) in groups.items():
            smoothed_rate = (cancels + base_rate * 30) / (bookings + 30)
            feature_rates[field][value] = smoothed_rate
            weighted_gap += bookings * abs(smoothed_rate - base_rate)
        importance_rows.append(
            {
                "feature": label,
                "importance_score": round(weighted_gap / len(facts), 4),
                "business_interpretation": feature_interpretation(field),
            }
        )

    importance_rows.sort(key=lambda r: r["importance_score"], reverse=True)
    total_importance = sum(r["importance_score"] for r in importance_rows) or 1
    for row in importance_rows:
        row["importance_share"] = round(row["importance_score"] / total_importance, 4)

    scored_sample = []
    risk_segments = defaultdict(lambda: defaultdict(float))
    rng = random.Random(42)
    sample_indexes = set(rng.sample(range(len(facts)), min(5000, len(facts))))
    for idx, row in enumerate(facts):
        score_logit = base_logit
        for field, _ in features:
            score_logit += 0.42 * (logit(feature_rates[field][row[field]]) - base_logit)
        score = sigmoid(score_logit)
        risk_band = "Low risk" if score < 0.25 else "Medium risk" if score < 0.45 else "High risk"
        risk_segments[risk_band]["bookings"] += 1
        risk_segments[risk_band]["cancellations"] += row["is_canceled"]
        risk_segments[risk_band]["lost_revenue"] += row["lost_revenue"]
        risk_segments[risk_band]["predicted_risk_sum"] += score
        if idx in sample_indexes:
            scored_sample.append(
                {
                    "booking_id": row["booking_id"],
                    "property_id": row["property_id"],
                    "market_segment": row["market_segment"],
                    "distribution_channel": row["distribution_channel"],
                    "lead_time_band": row["lead_time_band"],
                    "deposit_type": row["deposit_type"],
                    "actual_is_canceled": row["is_canceled"],
                    "predicted_cancellation_risk": round(score, 4),
                    "risk_band": risk_band,
                    "lost_revenue": row["lost_revenue"],
                }
            )

    risk_rows = []
    for risk_band, values in risk_segments.items():
        risk_rows.append(
            {
                "risk_band": risk_band,
                "bookings": int(values["bookings"]),
                "actual_cancellations": int(values["cancellations"]),
                "actual_cancellation_rate": round(pct(values["cancellations"], values["bookings"]), 4),
                "average_predicted_risk": round(pct(values["predicted_risk_sum"], values["bookings"]), 4),
                "lost_revenue": round(values["lost_revenue"], 2),
            }
        )
    risk_rows.sort(key=lambda r: ["Low risk", "Medium risk", "High risk"].index(r["risk_band"]))
    return importance_rows, scored_sample, risk_rows


def feature_interpretation(field: str) -> str:
    return {
        "lead_time_band": "Longer booking windows create more exposure to cancellation behavior.",
        "distribution_channel": "Channel behavior affects cancellation rate and net revenue after commission.",
        "market_segment": "Customer purpose and acquisition source change booking certainty.",
        "customer_type": "Contract, group, transient, and party bookings behave differently.",
        "deposit_type": "Deposit rules materially change cancellation incentives.",
        "special_request_band": "Special requests proxy customer commitment and trip intent.",
        "previous_cancel_band": "Prior cancellation history indicates repeat risk behavior.",
    }[field]


def logit(rate: float) -> float:
    bounded = min(max(rate, 0.0001), 0.9999)
    return math.log(bounded / (1 - bounded))


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def export_analytics(model: dict) -> dict:
    aggregates = aggregate_metrics(model)
    driver_rows = driver_analysis(model["fact_bookings"])
    opportunity_rows = opportunity_analysis(model["fact_bookings"])
    importance_rows, scored_sample, risk_rows = risk_model(model["fact_bookings"])

    summary = aggregates["executive_summary"]
    top_opp = opportunity_rows[0] if opportunity_rows else {}
    summary_rows = [
        summary
        | {
            "top_opportunity": " | ".join(
                str(top_opp.get(k, "")) for k in ["property_source", "market_segment", "distribution_channel", "lead_time_band"]
            ),
            "top_opportunity_recoverable_revenue": top_opp.get("estimated_recoverable_revenue", 0),
        }
    ]

    write_csv(PROCESSED / "monthly_kpi_summary.csv", aggregates["monthly_kpi_summary"])
    write_csv(PROCESSED / "channel_profitability.csv", aggregates["channel_profitability"])
    write_csv(OUTPUTS / "cancellation_driver_analysis.csv", driver_rows)
    write_csv(OUTPUTS / "segment_opportunity_rankings.csv", opportunity_rows)
    write_csv(OUTPUTS / "model_feature_importance.csv", importance_rows)
    write_csv(OUTPUTS / "model_scored_bookings_sample.csv", scored_sample)
    write_csv(OUTPUTS / "cancellation_risk_segments.csv", risk_rows)
    write_csv(OUTPUTS / "executive_summary.csv", summary_rows)
    return {
        "summary": summary_rows[0],
        "monthly": aggregates["monthly_kpi_summary"],
        "channel": aggregates["channel_profitability"],
        "drivers": driver_rows,
        "opportunities": opportunity_rows,
        "importance": importance_rows,
        "risk_segments": risk_rows,
    }


def svg_text(x: float, y: float, text: str, size: int = 12, weight: str = "400", anchor: str = "start") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#1f2933">{escape(str(text))}</text>'


def write_bar_svg(path: Path, title: str, rows: list[dict], label_key: str, value_key: str, subtitle: str, max_rows: int = 8) -> None:
    rows = rows[:max_rows]
    width, height = 960, 520
    left, top = 260, 92
    bar_h, gap = 32, 16
    plot_w = 610
    max_value = max((float(r[value_key]) for r in rows), default=1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(32, 40, title, 22, "700"),
        svg_text(32, 66, subtitle, 13),
    ]
    for i, row in enumerate(rows):
        y = top + i * (bar_h + gap)
        value = float(row[value_key])
        bar_w = 0 if max_value == 0 else (value / max_value) * plot_w
        parts.append(svg_text(32, y + 22, str(row[label_key])[:34], 12))
        parts.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="4" fill="#2563eb"/>')
        parts.append(svg_text(left + bar_w + 8, y + 21, money(value) if value > 1000 else f"{value:.1%}", 12))
    parts.append(svg_text(32, height - 24, "Source: StayWise generated analysis from public hotel booking data plus synthetic business context.", 11))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_line_svg(path: Path, monthly_rows: list[dict]) -> None:
    grouped = defaultdict(lambda: defaultdict(float))
    for row in monthly_rows:
        grouped[row["year_month"]]["realized_revenue"] += row["realized_revenue"]
        grouped[row["year_month"]]["lost_revenue"] += row["lost_revenue"]
    points = [(month, vals["realized_revenue"], vals["lost_revenue"]) for month, vals in sorted(grouped.items())]
    width, height = 1060, 520
    left, right, top, bottom = 72, 36, 86, 74
    plot_w, plot_h = width - left - right, height - top - bottom
    max_y = max((max(r, l) for _, r, l in points), default=1)

    def xy(index: int, value: float) -> tuple[float, float]:
        x = left + (index / max(len(points) - 1, 1)) * plot_w
        y = top + plot_h - (value / max_y) * plot_h
        return x, y

    realized = " ".join(f"{xy(i, p[1])[0]:.1f},{xy(i, p[1])[1]:.1f}" for i, p in enumerate(points))
    lost = " ".join(f"{xy(i, p[2])[0]:.1f},{xy(i, p[2])[1]:.1f}" for i, p in enumerate(points))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        svg_text(32, 40, "Monthly Realized Revenue and Lost Revenue", 22, "700"),
        svg_text(32, 66, "Monthly booking revenue, USD equivalent; lost revenue represents canceled booking value.", 13),
        f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#9aa5b1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#9aa5b1"/>',
        f'<polyline points="{realized}" fill="none" stroke="#2563eb" stroke-width="3"/>',
        f'<polyline points="{lost}" fill="none" stroke="#f97316" stroke-width="3"/>',
        '<rect x="760" y="34" width="14" height="14" fill="#2563eb"/>',
        svg_text(780, 46, "Realized revenue", 12),
        '<rect x="900" y="34" width="14" height="14" fill="#f97316"/>',
        svg_text(920, 46, "Lost revenue", 12),
    ]
    for i, (month, _, _) in enumerate(points):
        if i % 3 == 0 or i == len(points) - 1:
            x, _ = xy(i, 0)
            parts.append(svg_text(x, height - 42, month, 10, anchor="middle"))
    for step in range(5):
        value = max_y * step / 4
        y = top + plot_h - (value / max_y) * plot_h
        parts.append(f'<line x1="{left - 4}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#eef2f7"/>')
        parts.append(svg_text(left - 8, y + 4, f"${value/1_000_000:.1f}M", 10, anchor="end"))
    parts.append(svg_text(32, height - 18, "Source: StayWise generated analysis from public hotel booking data plus synthetic business context.", 11))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def build_charts(results: dict) -> None:
    chart_dir = OUTPUTS / "charts"
    write_line_svg(chart_dir / "monthly_revenue_trend.svg", results["monthly"])
    top_channel = sorted(results["channel"], key=lambda r: r["net_revenue"], reverse=True)
    write_bar_svg(
        chart_dir / "channel_net_revenue.svg",
        "Channel Net Revenue",
        top_channel,
        "distribution_channel",
        "net_revenue",
        "Realized revenue less estimated channel commission.",
    )
    top_opps = sorted(results["opportunities"], key=lambda r: r["estimated_recoverable_revenue"], reverse=True)
    for row in top_opps:
        row["opportunity_label"] = f"{row['market_segment']} | {row['distribution_channel']} | {row['lead_time_band']}"
    write_bar_svg(
        chart_dir / "recoverable_revenue_opportunities.svg",
        "Top Recoverable Revenue Opportunities",
        top_opps,
        "opportunity_label",
        "estimated_recoverable_revenue",
        "Estimated recoverable revenue from targeted cancellation reduction.",
    )
    high_drivers = sorted(
        [r for r in results["drivers"] if r["bookings"] >= 500],
        key=lambda r: r["cancellation_rate"],
        reverse=True,
    )
    for row in high_drivers:
        row["driver_label"] = f"{row['driver_type']}: {row['driver_value']}"
    write_bar_svg(
        chart_dir / "highest_cancellation_rate_drivers.svg",
        "Highest Cancellation Rate Drivers",
        high_drivers,
        "driver_label",
        "cancellation_rate",
        "Groups with at least 500 bookings; values are cancellation rates.",
    )


def col_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell_xml(row_idx: int, col_idx: int, value, style: int = 0, formula: bool = False) -> str:
    ref = f"{col_name(col_idx)}{row_idx}"
    style_attr = f' s="{style}"' if style else ""
    if formula:
        return f'<c r="{ref}"{style_attr}><f>{escape(str(value).lstrip("="))}</f></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"{style_attr}><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(str(value))}</t></is></c>'


def worksheet_xml(rows: list[list], styles: list[list[int]] | None = None, formulas: set[tuple[int, int]] | None = None) -> str:
    styles = styles or []
    formulas = formulas or set()
    row_xml = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            style = styles[r_idx - 1][c_idx - 1] if r_idx - 1 < len(styles) and c_idx - 1 < len(styles[r_idx - 1]) else 0
            cells.append(cell_xml(r_idx, c_idx, value, style, (r_idx, c_idx) in formulas))
        row_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="10" width="24" customWidth="1"/></cols>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="5">
    <font><sz val="11"/><color rgb="FF000000"/><name val="Arial"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>
    <font><sz val="11"/><color rgb="FF0000FF"/><name val="Arial"/></font>
    <font><sz val="11"/><color rgb="FF008000"/><name val="Arial"/></font>
    <font><b/><sz val="14"/><color rgb="FF1F2933"/><name val="Arial"/></font>
  </fonts>
  <fills count="5">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFFF00"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFEFF6FF"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="8">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def create_xlsx(path: Path, sheets: list[tuple[str, list[list], list[list[int]], set[tuple[int, int]]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        sheet_overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(sheets) + 1)
        )
        zf.writestr(
            "[Content_Types].xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {sheet_overrides}
</Types>""",
        )
        zf.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        sheet_tags = "".join(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
            for i, (name, _, _, _) in enumerate(sheets, start=1)
        )
        zf.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheet_tags}</sheets>
  <calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>
</workbook>""",
        )
        rels = "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(sheets) + 1)
        )
        rels += f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>""",
        )
        zf.writestr("xl/styles.xml", styles_xml())
        for i, (_, rows, styles, formulas) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", worksheet_xml(rows, styles, formulas))


def build_excel(results: dict) -> None:
    summary = results["summary"]
    top_opps = results["opportunities"][:10]
    base = [
        ["Metric", "Value", "Source / Definition"],
        ["Realized Revenue", summary["realized_revenue"], "Stay revenue plus retained cancellation fee revenue"],
        ["Stay Revenue", summary["stay_revenue"], "Room revenue from non-canceled stays"],
        ["Potential Revenue", summary["potential_revenue"], "All booking value before cancellation loss"],
        ["Lost Revenue", summary["lost_revenue"], "Canceled booking value after deposit recovery"],
        ["Net Revenue", summary["net_revenue"], "Realized revenue less estimated channel commission"],
        ["Cancellation Rate", summary["cancellation_rate"], "Canceled bookings / total bookings"],
        ["Occupancy Rate", summary["occupancy_rate"], "Realized room nights / available room nights"],
        ["Commission Cost", summary["commission_cost"], "Estimated channel cost from synthetic rates"],
        ["Cancellation Fee Revenue", summary["cancellation_fee_revenue"], "Synthetic retained cancellation fee from deposit rules"],
        ["RevPAR", summary["revpar"], "Realized revenue / available room nights"],
        ["Net RevPAR", summary["net_revpar"], "Net revenue / available room nights"],
    ]
    base_styles = [[1, 1, 1]] + [[0, 5 if i in (2, 3, 4, 5, 6, 9, 10, 11, 12) else 6 if i in (7, 8) else 0, 0] for i in range(2, len(base) + 1)]

    control = [
        ["StayWise Scenario Control Panel", "", ""],
        ["Input", "Value", "Notes"],
        ["Cancellation reduction", 0.05, "Blue/yellow inputs are scenario assumptions"],
        ["ADR uplift", 0.03, "User can change this assumption"],
        ["Occupancy uplift", 0.02, "User can change this assumption"],
        ["Channel mix improvement", 0.04, "Share of commission cost that can be reduced"],
        ["Base realized revenue", "='Base Metrics'!B2", "Linked from Base Metrics"],
        ["Base lost revenue", "='Base Metrics'!B4", "Linked from Base Metrics"],
        ["Base commission cost", "='Base Metrics'!B9", "Linked from Base Metrics"],
    ]
    control_styles = [[4, 0, 0], [1, 1, 1]] + [[0, 2, 0] for _ in range(4)] + [[0, 3, 0] for _ in range(3)]
    control_formulas = {(7, 2), (8, 2), (9, 2)}

    scenarios = [
        ["Scenario", "Cancellation Reduction", "ADR Uplift", "Occupancy Uplift", "Channel Mix Improvement", "Recovered Revenue", "ADR Impact", "Occupancy Impact", "Channel Cost Savings", "Total Incremental Revenue", "New Revenue", "Revenue Lift"],
        ["Base", 0.00, 0.00, 0.00, 0.00, "='Base Metrics'!$B$5*B2", "='Base Metrics'!$B$2*C2", "='Base Metrics'!$B$2*D2", "='Base Metrics'!$B$9*E2", "=SUM(F2:I2)", "='Base Metrics'!$B$2+J2", "=J2/'Base Metrics'!$B$2"],
        ["Conservative", 0.03, 0.01, 0.01, 0.02, "='Base Metrics'!$B$5*B3", "='Base Metrics'!$B$2*C3", "='Base Metrics'!$B$2*D3", "='Base Metrics'!$B$9*E3", "=SUM(F3:I3)", "='Base Metrics'!$B$2+J3", "=J3/'Base Metrics'!$B$2"],
        ["Expected", 0.05, 0.03, 0.02, 0.04, "='Base Metrics'!$B$5*B4", "='Base Metrics'!$B$2*C4", "='Base Metrics'!$B$2*D4", "='Base Metrics'!$B$9*E4", "=SUM(F4:I4)", "='Base Metrics'!$B$2+J4", "=J4/'Base Metrics'!$B$2"],
        ["Aggressive", 0.08, 0.05, 0.04, 0.07, "='Base Metrics'!$B$5*B5", "='Base Metrics'!$B$2*C5", "='Base Metrics'!$B$2*D5", "='Base Metrics'!$B$9*E5", "=SUM(F5:I5)", "='Base Metrics'!$B$2+J5", "=J5/'Base Metrics'!$B$2"],
    ]
    scenario_styles = [[1] * 12] + [[0, 2, 2, 2, 2, 0, 0, 0, 0, 5, 5, 6] for _ in range(4)]
    scenario_formulas = {(r, c) for r in range(2, 6) for c in range(6, 13)}

    sensitivity = [["ADR Uplift \\ Cancellation Reduction", 0.02, 0.04, 0.06, 0.08, 0.10]]
    for adr in [0.00, 0.01, 0.02, 0.03, 0.04, 0.05]:
        row_idx = len(sensitivity) + 1
        row = [adr]
        for c in range(2, 7):
            row.append(f"='Base Metrics'!$B$5*{col_name(c)}$1+'Base Metrics'!$B$2*$A{row_idx}")
        sensitivity.append(row)
    sensitivity_styles = [[1] * 6] + [[2] + [5] * 5 for _ in range(6)]
    sensitivity_formulas = {(r, c) for r in range(2, 8) for c in range(2, 7)}

    backlog = [["Rank", "Opportunity", "Bookings", "Cancellation Rate", "Lost Revenue", "Recoverable Revenue", "Recommended Intervention"]]
    for row in top_opps:
        backlog.append(
            [
                row["priority_rank"],
                f"{row['property_source']} | {row['market_segment']} | {row['distribution_channel']} | {row['lead_time_band']}",
                row["bookings"],
                row["cancellation_rate"],
                row["lost_revenue"],
                row["estimated_recoverable_revenue"],
                row["recommended_intervention"],
            ]
        )
    backlog_styles = [[1] * 7] + [[0, 0, 0, 6, 5, 5, 0] for _ in top_opps]

    readme = [
        ["StayWise Scenario Model"],
        ["Purpose", "Evaluate cancellation, ADR, occupancy, and channel-mix interventions."],
        ["Source", "Generated from StayWise public hotel booking data plus synthetic operating context."],
        ["Input convention", "Blue text with yellow fill marks user-changeable assumptions."],
        ["Formula convention", "Scenario calculations use Excel formulas so the model remains editable."],
    ]
    readme_styles = [[4], [1, 0], [1, 0], [1, 0], [1, 0]]

    create_xlsx(
        EXCEL / "StayWise_Scenario_Model.xlsx",
        [
            ("README", readme, readme_styles, set()),
            ("Control Panel", control, control_styles, control_formulas),
            ("Base Metrics", base, base_styles, set()),
            ("Scenarios", scenarios, scenario_styles, scenario_formulas),
            ("Sensitivity", sensitivity, sensitivity_styles, sensitivity_formulas),
            ("Intervention Backlog", backlog, backlog_styles, set()),
        ],
    )


def write_generated_docs(results: dict) -> None:
    summary = results["summary"]
    top_opp = results["opportunities"][0]
    top_feature = results["importance"][0]

    (DOCS / "Executive_Recommendation_Memo.md").write_text(
        f"""# Executive Recommendation Memo

## Business Question

How can StayWise recover avoidable revenue leakage from cancellations, underutilized inventory, and unprofitable channel mix?

## Executive Summary

The analysis found **{money(summary['lost_revenue'])}** in cancellation-linked revenue leakage across **{summary['bookings']:,}** bookings after applying deposit-based cancellation fee recovery. The current cancellation rate is **{percent(summary['cancellation_rate'])}**, retained cancellation fee revenue is **{money(summary['cancellation_fee_revenue'])}**, and estimated net revenue after channel commission is **{money(summary['net_revenue'])}**.

The highest-priority opportunity is **{top_opp['property_source']} | {top_opp['market_segment']} | {top_opp['distribution_channel']} | {top_opp['lead_time_band']}**, with an estimated **{money(top_opp['estimated_recoverable_revenue'])}** recoverable revenue opportunity.

## Recommended Action

Prioritize: **{top_opp['recommended_intervention']}**.

This intervention is recommended because the segment combines high booking volume, high cancellation exposure, and a meaningful recoverable revenue estimate. The strongest modeled cancellation-risk driver is **{top_feature['feature']}**, which supports targeting the intervention through booking behavior rather than applying a generic policy to all customers.

## Decision Logic

- Revenue leakage was defined as canceled booking value less assumed cancellation fee recovery by deposit type.
- Net revenue was defined as realized revenue less estimated channel commission.
- Recoverable revenue was estimated from segment-level lost revenue and achievable cancellation-rate reduction.
- Recommendations were ranked by recoverable revenue, cancellation risk, and booking volume.

## KPI Monitoring After Implementation

- Cancellation rate by lead-time band and channel
- Realized revenue and lost revenue
- Net RevPAR
- Direct share of bookings
- Recovery against estimated opportunity

## Caveats

The hotel booking data is public and historical. Channel commission, inventory, targets, events, and intervention metadata are synthetic business context tables created for portfolio demonstration. They should be treated as realistic assumptions, not actual company records.
""",
        encoding="utf-8",
    )

    (DOCS / "Data_Dictionary.md").write_text(DATA_DICTIONARY_MD, encoding="utf-8")


DATA_DICTIONARY_MD = """# Data Dictionary

Grain of the model: **one row in `fact_bookings` = one hotel reservation** (119,390 rows, arrivals Jul 2015 - Aug 2017, two properties in Portugal).

Every column is tagged with its origin:

- **Source** - taken directly from the public Hotel Booking Demand dataset (`data/raw/hotels.csv`).
- **Derived** - calculated from source columns by `scripts/build_staywise.py` using a documented rule.
- **Synthetic** - an assumption created for this portfolio project because the public dataset does not include it (commission rates, room inventory, deposit recovery, targets). A real hotel would replace these with actuals.

## fact_bookings

| Column | Origin | Description |
|---|---|---|
| booking_id | Derived | Surrogate key `SW000001`... assigned in raw-file order. |
| arrival_date, date_id, arrival_year_month | Derived | Built from `arrival_date_year/month/day_of_month`. `date_id` is `YYYYMMDD` and joins to `dim_date`. |
| property_id | Derived | `P001` = Resort Hotel, `P002` = City Hotel. Joins to `dim_property`. |
| channel_id, market_segment_id, customer_type_id, room_type_id, country_id | Derived | Surrogate keys joining to the matching dimension tables. |
| hotel_source, distribution_channel, market_segment, customer_type, reserved_room_type, deposit_type, reservation_status | Source | Descriptive labels kept on the fact for convenience (denormalized copies of dimension values). |
| lead_time | Source | Days between booking date and arrival. |
| lead_time_band | Derived | 0-7, 8-30, 31-90, 91-180, 181+ days. |
| stay_nights | Derived | `stays_in_weekend_nights + stays_in_week_nights`, floored at 1. |
| stay_band | Derived | 1 night, 2-3, 4-7, 8+ nights. |
| guests | Derived | adults + children + babies, floored at 1. |
| adr | Source | Average Daily Rate quoted on the booking (negative values floored at 0). |
| is_canceled | Source | 1 if the reservation was canceled, else 0. |
| potential_revenue | Derived | `adr * stay_nights` - the value of the booking if it had been honored. |
| stay_revenue | Derived | `potential_revenue` if not canceled, else 0. |
| deposit_recovery_rate | Synthetic | Share of a canceled booking's value the hotel keeps: Non Refund 85%, Refundable 20%, No Deposit 0%. |
| cancellation_fee_revenue | Derived | `potential_revenue * deposit_recovery_rate` when canceled, else 0. |
| realized_revenue | Derived | `stay_revenue + cancellation_fee_revenue` - money actually kept. |
| lost_revenue | Derived | `potential_revenue - realized_revenue` when canceled, else 0. Identity: potential = realized + lost. |
| commission_rate | Synthetic | Channel cost assumption from `dim_channel`: Direct 2%, Corporate 3%, GDS 10%, TA/TO 18%, Undefined 12%. |
| commission_cost | Derived | `realized_revenue * commission_rate`. |
| net_revenue | Derived | `realized_revenue - commission_cost`. |
| room_nights_booked | Derived | `stay_nights`. |
| room_nights_realized | Derived | `stay_nights` if not canceled, else 0. Numerator of occupancy. |
| previous_cancellations, previous_cancel_band | Source / Derived | Count of the guest's prior cancellations; banded 0, 1, 2+. |
| total_special_requests, special_request_band | Source / Derived | Count of special requests; banded 0, 1, 2+. |
| booking_changes, days_in_waiting_list, required_car_parking_spaces | Source | Behavioral fields kept for analysis. |
| room_mismatch_flag | Derived | 1 if the assigned room type differs from the reserved room type. |

## Dimension tables

| Table | Origin | Columns | Notes |
|---|---|---|---|
| dim_date | Derived | date_id, date, year, month_number, month_name, quarter, year_month, day_of_week, is_weekend | One row per arrival date present in the data. |
| dim_property | Synthetic | property_id, property_name, property_type, city, country, room_count, target_adr, target_occupancy | Names, cities, room counts (280 resort / 450 city) and targets are assumptions; the Resort/City split is from source. |
| dim_channel | Synthetic | channel_id, distribution_channel, channel_name, channel_group, commission_rate | Channel names are from source; commission rates are assumptions. |
| dim_market_segment | Source | market_segment_id, market_segment | Online TA, Offline TA/TO, Direct, Groups, Corporate, Aviation, Complementary, Undefined. |
| dim_customer | Source | customer_type_id, customer_type | Transient, Transient-Party, Contract, Group. |
| dim_room_type | Source | room_type_id, room_type | Reserved room type codes A-L. |
| dim_country | Source | country_id, country_code, country_name | Guest country ISO code. |
| dim_intervention_options | Synthetic | intervention_id, intervention_name, primary_driver, owner_role, expected_kpi, implementation_effort | Catalogue of candidate actions for the action tracker. |

## Supporting fact tables

| Table | Origin | Grain | Notes |
|---|---|---|---|
| fact_daily_inventory | Synthetic | property x day | `available_room_nights` = room_count adjusted +/-2% by season. Denominator of occupancy and RevPAR. Because the public dataset is a sample of bookings rather than the hotels' full ledger, modeled occupancy (about 44%) is lower than a real hotel would report; the ratio is still valid for comparing months, properties and scenarios. |
| fact_monthly_targets | Synthetic | property x month | Target occupancy, ADR and cancellation rate for variance reporting. |
| fact_local_events | Synthetic | property x month | Local event intensity and competitor rate index for context. |

## Analytical outputs (`outputs/`, `data/processed/`)

| File | Grain | Produced by |
|---|---|---|
| executive_summary.csv | whole portfolio | `aggregate_metrics()` |
| monthly_kpi_summary.csv | property x month | `aggregate_metrics()` |
| channel_profitability.csv | property x channel | `aggregate_metrics()` |
| cancellation_driver_analysis.csv | one driver value per row (8 drivers) | `driver_analysis()` |
| segment_opportunity_rankings.csv | property x segment x channel x lead band x deposit (min 120 bookings) | `opportunity_analysis()` |
| model_feature_importance.csv, cancellation_risk_segments.csv, model_scored_bookings_sample.csv | feature / risk band / sampled booking | `risk_model()` - an interpretable rule-based risk score, not a trained ML model |
"""


def write_static_docs() -> None:
    (DOCS / "Business_Requirements_Document.md").write_text(
        """# Business Requirements Document

## Project

StayWise — Hospitality Revenue & Decision Intelligence Platform

## Business Problem

Hotel leadership lacks a unified view of revenue leakage caused by cancellations, underutilized inventory, and unprofitable distribution channels. Current reporting describes bookings but does not help stakeholders decide which intervention should be prioritized.

## Objectives

- Define trusted KPIs for revenue, occupancy, ADR, RevPAR, net RevPAR, cancellation rate, lost revenue, and channel profitability.
- Identify which segments, channels, and booking behaviors create the largest revenue leakage.
- Provide a scenario model for evaluating cancellation, ADR, occupancy, and channel-mix interventions.
- Deliver a Mac-ready decision dashboard and Power BI-ready datasets for stakeholder review.

## Stakeholders

- General Manager: revenue recovery and operating performance.
- Revenue Manager: pricing, cancellation policy, and channel mix.
- Marketing Lead: direct booking and segment targeting.
- Operations Manager: pre-arrival workflows and service interventions.
- Finance Analyst: KPI definitions and revenue reconciliation.

## Functional Requirements

- Load raw hotel booking data and preserve it separately from processed datasets.
- Create a dimensional model with booking facts and conformed business dimensions.
- Calculate cancellation rate, realized revenue, lost revenue, occupancy, ADR, RevPAR, net RevPAR, and channel commission cost.
- Segment revenue leakage by property, market segment, channel, lead-time band, customer type, and deposit type.
- Rank opportunities by recoverable revenue and recommended intervention.
- Export Power BI-ready CSVs and DAX measure definitions.
- Generate an Excel scenario model with editable assumptions.
- Provide a local dashboard that supports the executive decision workflow on macOS.

## Non-Functional Requirements

- Analysis must be reproducible from command line.
- Metric definitions must be documented and traceable.
- Synthetic data must be clearly labeled.
- Dashboard outputs must be understandable to non-technical stakeholders.

## Out of Scope

- Live hotel PMS integration.
- Real-time data refresh.
- Deployment of a production Power BI service workspace.
- Actual policy rollout measurement after implementation.
""",
        encoding="utf-8",
    )

    (DOCS / "Stakeholder_Map.md").write_text(
        """# Stakeholder Map

| Stakeholder | Decision Need | Primary KPIs | Deliverable |
|---|---|---|---|
| General Manager | Which intervention should be prioritized? | Net revenue, RevPAR, occupancy, lost revenue | Executive Overview and recommendation memo |
| Revenue Manager | Which segments need pricing or cancellation policy changes? | ADR, cancellation rate, lost revenue, lead-time risk | Revenue Diagnostics and Cancellation Root Cause pages |
| Marketing Lead | Which channels should receive demand-shift investment? | Direct share, channel profitability, commission cost | Channel Profitability page |
| Operations Manager | Which pre-arrival workflows reduce preventable cancellations? | High-risk bookings, special requests, realized room nights | Action Tracker |
| Finance Analyst | Are KPI definitions reconciled and auditable? | Revenue, net revenue, commission cost, RevPAR | KPI dictionary, SQL views, UAT tests |
""",
        encoding="utf-8",
    )

    (DOCS / "KPI_Dictionary.md").write_text(
        """# KPI Dictionary

All revenue KPIs are calculated once at booking grain in `scripts/build_staywise.py`, stored on `fact_bookings`, and then summed. The same definitions are implemented in SQL (`sql/04_metric_views.sql`), DAX (`powerbi/StayWise_DAX_Measures.dax`), Excel and the dashboard so every surface reconciles.

## Revenue KPIs

| KPI | Definition | Formula | Grain | Owner |
|---|---|---|---|---|
| Potential Revenue | Value of the booking if honored, before any cancellation impact | `adr * stay_nights` | Booking | Finance Analyst |
| Stay Revenue | Room revenue from stays that actually happened | `potential_revenue` if not canceled, else 0 | Booking | Finance Analyst |
| Cancellation Fee Revenue | Money kept from a canceled booking under the deposit policy (synthetic recovery rates: Non Refund 85%, Refundable 20%, No Deposit 0%) | `potential_revenue * deposit_recovery_rate` if canceled, else 0 | Booking | Finance Analyst |
| Realized Revenue | Money the hotel actually kept | `stay_revenue + cancellation_fee_revenue` | Booking | Finance Analyst |
| Lost Revenue | Revenue leakage: canceled value the hotel did not keep | `potential_revenue - realized_revenue` if canceled, else 0 | Booking | Revenue Manager |
| Channel Commission Cost | Estimated cost of acquiring the booking through its channel (synthetic rates: Direct 2%, Corporate 3%, GDS 10%, TA/TO 18%) | `realized_revenue * commission_rate` | Booking / channel | Marketing Lead |
| Net Revenue | Realized revenue after channel cost | `realized_revenue - commission_cost` | Booking | Finance Analyst |

**Reconciliation identity:** `Potential Revenue = Realized Revenue + Lost Revenue` for every booking. This is checked in `sql/03_quality_checks.sql`, `scripts/validate_outputs.py` and the notebook.

## Operating KPIs

| KPI | Definition | Formula | Grain | Owner |
|---|---|---|---|---|
| Cancellation Rate | Share of bookings that were canceled | `SUM(is_canceled) / COUNT(bookings)` | Any selected grain | Revenue Manager |
| Room Nights Realized | Nights actually stayed | `stay_nights` if not canceled, else 0 | Booking | General Manager |
| Available Room Nights | Capacity (synthetic): rooms available per property per day, summed over the period | `SUM(fact_daily_inventory.available_room_nights)` | Property-date | General Manager |
| Occupancy Rate | Share of capacity that was sold and used | `room_nights_realized / available_room_nights` | Property-period | General Manager |
| ADR (Average Daily Rate) | Average revenue per occupied room night | `realized_revenue / room_nights_realized` | Property-period | Revenue Manager |
| RevPAR (Revenue per Available Room) | Revenue per room the hotel *could* have sold; combines price and occupancy (`RevPAR = ADR * Occupancy`) | `realized_revenue / available_room_nights` | Property-period | Revenue Manager |
| Net RevPAR | RevPAR after channel commission | `net_revenue / available_room_nights` | Property-period | Finance Analyst |

## Prioritization KPIs (segment grain, `outputs/segment_opportunity_rankings.csv`)

| KPI | Definition | Formula | Owner |
|---|---|---|---|
| Excess Cancellation Rate | How much worse a segment cancels than the portfolio average (37.0%) | `MAX(segment_cancellation_rate - portfolio_cancellation_rate, 0)` | Revenue Manager |
| Achievable Cancellation Reduction | Assumed share of a segment's lost revenue a targeted intervention could recover. Rule: 65% of the excess rate, never below 6% (any segment can improve a little) and never above 35% (no intervention removes most cancellations) | `MIN(0.35, MAX(0.06, excess_cancellation_rate * 0.65))` | General Manager |
| Recoverable Revenue | Sizing of the opportunity - a prioritization estimate, not measured impact | `segment_lost_revenue * achievable_cancellation_reduction` | General Manager |
| Priority Score | Ranking score that balances money, risk and reach so a huge low-risk segment and a tiny high-risk segment do not both dominate | `recoverable_revenue / 1000 + cancellation_rate * 25 + bookings / 1000` | General Manager |
| Minimum Segment Size | Segments with fewer than 120 bookings are excluded from ranking to avoid acting on noise | `bookings >= 120` | Finance Analyst |
""",
        encoding="utf-8",
    )

    (DOCS / "User_Stories_Acceptance_Criteria.md").write_text(
        """# User Stories and Acceptance Criteria

| ID | User Story | Acceptance Criteria |
|---|---|---|
| US-01 | As a General Manager, I want an executive KPI view so I can see whether revenue recovery is improving. | Dashboard shows realized revenue, lost revenue, occupancy, ADR, RevPAR, net RevPAR, and cancellation rate. |
| US-02 | As a Revenue Manager, I want cancellation drivers by segment and lead-time band so I can target policy changes. | Users can filter by property, channel, segment, and month; cancellation-rate visuals update consistently. |
| US-03 | As a Marketing Lead, I want channel profitability after commission so I can compare direct and OTA channels. | Channel page includes realized revenue, commission cost, net revenue, and cancellation rate. |
| US-04 | As a Finance Analyst, I want KPI definitions documented so metric calculations can be audited. | KPI dictionary, SQL views, and Power BI DAX use consistent definitions. |
| US-05 | As a stakeholder, I want scenario assumptions so I can evaluate intervention tradeoffs. | Excel model allows changes to cancellation reduction, ADR uplift, occupancy uplift, and channel-mix improvement. |
| US-06 | As an interviewer, I want a local decision surface so I can review the analysis on macOS. | The local dashboard filters booking data, shows the ranked action backlog, and reconciles to executive KPIs. |
""",
        encoding="utf-8",
    )

    (DOCS / "Requirements_Traceability_Matrix.md").write_text(
        """# Requirements Traceability Matrix

| Requirement | SQL Asset | Python / Output Asset | Excel / Dashboard Asset | UAT Case |
|---|---|---|---|---|
| Define revenue KPIs | `vw_executive_kpis` | `executive_summary.csv` | Base Metrics and Executive Overview | UAT-01 |
| Diagnose cancellation leakage | `vw_cancellation_drivers` | `cancellation_driver_analysis.csv` | Cancellation Root Cause page | UAT-02 |
| Compare channel profitability | `vw_channel_profitability` | `channel_profitability.csv` | Channel Profitability page | UAT-03 |
| Rank interventions | `vw_opportunity_rankings` | `segment_opportunity_rankings.csv` | Action Tracker and Backlog | UAT-04 |
| Model business scenarios | N/A | `executive_summary.csv` | Scenario Model workbook | UAT-05 |
| Demonstrate the operating decision | `vw_opportunity_rankings` | `segment_opportunity_rankings.csv` | Mac Decision Console | UAT-06 |
""",
        encoding="utf-8",
    )

    (DOCS / "UAT_Test_Cases.md").write_text(
        """# UAT Test Cases

| Test ID | Scenario | Expected Result |
|---|---|---|
| UAT-01 | Compare total realized revenue in SQL view, Power BI import, and Excel Base Metrics. | Values match after rounding. |
| UAT-02 | Filter cancellation analysis to TA/TO and 91-180 day lead-time band. | Dashboard and CSV show consistent cancellation rate and lost revenue. |
| UAT-03 | Compare channel net revenue against realized revenue less commission cost. | Net revenue formula reconciles for each channel. |
| UAT-04 | Sort opportunity table by priority rank. | Rank 1 shows the largest risk-adjusted recoverable revenue opportunity. |
| UAT-05 | Change Excel cancellation reduction from 5% to 8%. | Recovered revenue and total incremental revenue update through formulas. |
| UAT-06 | Select a single property in Power BI. | KPI cards, trends, and channel breakdowns filter to that property. |
| UAT-07 | Review executive memo without technical context. | Reader can identify the business problem, top opportunity, recommended action, and KPI monitoring plan. |
| UAT-08 | Apply a property and channel filter in the Mac Decision Console. | KPI cards, trend, drivers, channels, scenario, and action backlog use the filtered booking population. |
""",
        encoding="utf-8",
    )


def write_powerbi_docs() -> None:
    (POWERBI / "DAX_Measures.md").write_text(
        """# Power BI DAX Measures

```DAX
Total Bookings = COUNTROWS(fact_bookings)

Cancellations = SUM(fact_bookings[is_canceled])

Cancellation Rate = DIVIDE([Cancellations], [Total Bookings])

Potential Revenue = SUM(fact_bookings[potential_revenue])

Realized Revenue = SUM(fact_bookings[realized_revenue])

Lost Revenue = SUM(fact_bookings[lost_revenue])

Cancellation Fee Revenue = SUM(fact_bookings[cancellation_fee_revenue])

Commission Cost = SUM(fact_bookings[commission_cost])

Net Revenue = [Realized Revenue] - [Commission Cost]

Room Nights Realized = SUM(fact_bookings[room_nights_realized])

Available Room Nights = SUM(fact_daily_inventory[available_room_nights])

Occupancy Rate = DIVIDE([Room Nights Realized], [Available Room Nights])

ADR = DIVIDE([Realized Revenue], [Room Nights Realized])

RevPAR = DIVIDE([Realized Revenue], [Available Room Nights])

Net RevPAR = DIVIDE([Net Revenue], [Available Room Nights])

Revenue Opportunity = SUM(segment_opportunity_rankings[estimated_recoverable_revenue])
```
""",
        encoding="utf-8",
    )

    (POWERBI / "Dashboard_Page_Spec.md").write_text(
        """# Power BI Dashboard Page Specification

## Page 1: Executive Overview

- KPI cards: Realized Revenue, Lost Revenue, Occupancy Rate, ADR, RevPAR, Net RevPAR, Cancellation Rate.
- Line chart: monthly realized revenue and lost revenue.
- Bar chart: top recoverable revenue opportunities.
- Filters: property, year-month, distribution channel, market segment.

## Page 2: Revenue Diagnostics

- Monthly revenue trend by property.
- Variance table by property and channel.
- Drilldown from property to channel to segment.

## Page 3: Cancellation Root Cause

- Cancellation rate by lead-time band, channel, market segment, deposit type, and customer type.
- Feature-importance table from the interpretable, rule-based cancellation risk score (not a trained ML model).
- Risk segment summary table.

## Page 4: Channel Profitability

- Gross realized revenue vs net revenue by channel.
- Commission cost by channel.
- Cancellation rate by channel.

## Page 5: Scenario Planner

- Import scenario outputs from `excel/StayWise_Scenario_Model.xlsx` or recreate the scenario table in Power BI.
- Show conservative, expected, and aggressive incremental revenue scenarios.

## Page 6: Action Tracker

- Opportunity table with rank, segment, channel, lead-time band, recoverable revenue, and recommended intervention.
- Status fields can be added manually for portfolio demo screenshots.
""",
        encoding="utf-8",
    )

    (POWERBI / "PowerBI_Build_Guide.md").write_text(
        """# Power BI Build Guide

## Generated Power BI Project Scaffold

This repo includes a generated Power BI Project scaffold:

`powerbi/StayWise_PowerBI_Project/StayWise.pbip`

Open this file in Power BI Desktop on Windows, refresh the model, build or verify the report pages, and save the final dashboard as `powerbi/StayWise_Dashboard.pbix`.

To regenerate the scaffold:

```sh
make powerbi
```

The scaffold includes CSV import queries, semantic-model relationships, and DAX measures. Power BI Desktop is still required to create the final `.pbix` file.

## Import Tables

Import these CSV files:

- `data/processed/fact_bookings.csv`
- `data/processed/fact_daily_inventory.csv`
- `data/processed/dim_date.csv`
- `data/processed/dim_property.csv`
- `data/processed/dim_channel.csv`
- `data/processed/dim_market_segment.csv`
- `data/processed/dim_customer.csv`
- `data/processed/dim_room_type.csv`
- `data/processed/monthly_kpi_summary.csv`
- `data/processed/channel_profitability.csv`
- `outputs/segment_opportunity_rankings.csv`
- `outputs/cancellation_driver_analysis.csv`
- `outputs/model_feature_importance.csv`
- `outputs/cancellation_risk_segments.csv`

## Relationships

- `fact_bookings[date_id]` to `dim_date[date_id]`
- `fact_bookings[property_id]` to `dim_property[property_id]`
- `fact_bookings[channel_id]` to `dim_channel[channel_id]`
- `fact_bookings[market_segment_id]` to `dim_market_segment[market_segment_id]`
- `fact_daily_inventory[date_id]` to `dim_date[date_id]`
- `fact_daily_inventory[property_id]` to `dim_property[property_id]`

## Design Notes

Use a quiet executive dashboard style. The first page should answer the decision question before any filter interaction: where is revenue leakage concentrated and which intervention should leadership prioritize?
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    download_raw(force=args.force_download)
    if args.download_only:
        return

    raw_rows = read_raw_rows()
    model = build_model(raw_rows)
    export_model(model)
    results = export_analytics(model)
    build_charts(results)
    build_excel(results)
    write_static_docs()
    write_generated_docs(results)
    write_powerbi_docs()
    print(f"Built StayWise project with {len(model['fact_bookings']):,} bookings.")
    print(f"Top opportunity: {results['summary']['top_opportunity']}")


if __name__ == "__main__":
    main()
