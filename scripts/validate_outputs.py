#!/usr/bin/env python3
"""Validate generated StayWise outputs without third-party dependencies."""

from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "data/raw/hotels.csv",
    "data/processed/fact_bookings.csv",
    "data/processed/dim_date.csv",
    "data/processed/dim_property.csv",
    "data/processed/dim_channel.csv",
    "data/processed/monthly_kpi_summary.csv",
    "data/processed/channel_profitability.csv",
    "outputs/executive_summary.csv",
    "outputs/segment_opportunity_rankings.csv",
    "outputs/cancellation_driver_analysis.csv",
    "outputs/model_feature_importance.csv",
    "outputs/charts/monthly_revenue_trend.svg",
    "outputs/charts/channel_net_revenue.svg",
    "outputs/charts/recoverable_revenue_opportunities.svg",
    "outputs/charts/highest_cancellation_rate_drivers.svg",
    "excel/StayWise_Scenario_Model.xlsx",
    "docs/Executive_Recommendation_Memo.md",
    "docs/KPI_Dictionary.md",
    "docs/Data_Dictionary.md",
    "notebooks/StayWise_Analysis_Notebook.ipynb",
    "powerbi/DAX_Measures.md",
    "dashboard/index.html",
    "dashboard/app.js",
    "dashboard/styles.css",
    "scripts/serve_dashboard.py",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def as_float(value: str) -> float:
    return float(value or 0)


def validate_files(errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            errors.append(f"Missing required file: {relative}")
        elif path.stat().st_size == 0:
            errors.append(f"Empty required file: {relative}")


def validate_fact_reconciliation(errors: list[str]) -> None:
    facts = read_csv(ROOT / "data/processed/fact_bookings.csv")
    if len(facts) != 119_390:
        errors.append(f"Expected 119,390 booking rows; found {len(facts):,}")

    potential = realized = lost = 0.0
    bad_rows = 0
    for row in facts:
        p = as_float(row["potential_revenue"])
        r = as_float(row["realized_revenue"])
        l = as_float(row["lost_revenue"])
        potential += p
        realized += r
        lost += l
        if abs(p - (r + l)) > 0.011:
            bad_rows += 1
        if p < 0 or r < 0 or l < 0:
            bad_rows += 1

    if bad_rows:
        errors.append(f"Revenue reconciliation failed for {bad_rows} fact rows")

    summary = read_csv(ROOT / "outputs/executive_summary.csv")[0]
    if abs(as_float(summary["potential_revenue"]) - potential) > 1:
        errors.append("Executive summary potential revenue does not reconcile to fact_bookings")
    if abs(as_float(summary["realized_revenue"]) - realized) > 1:
        errors.append("Executive summary realized revenue does not reconcile to fact_bookings")
    if abs(as_float(summary["lost_revenue"]) - lost) > 1:
        errors.append("Executive summary lost revenue does not reconcile to fact_bookings")


def validate_rankings(errors: list[str]) -> None:
    rows = read_csv(ROOT / "outputs/segment_opportunity_rankings.csv")
    ranks = [int(row["priority_rank"]) for row in rows]
    if ranks != sorted(ranks):
        errors.append("Opportunity rankings are not sorted by priority_rank")
    if rows and rows[0]["priority_rank"] != "1":
        errors.append("Top opportunity does not start at priority rank 1")


def validate_workbook(errors: list[str]) -> None:
    workbook_path = ROOT / "excel/StayWise_Scenario_Model.xlsx"
    expected_sheets = {"README", "Control Panel", "Base Metrics", "Scenarios", "Sensitivity", "Intervention Backlog"}
    try:
        with zipfile.ZipFile(workbook_path) as zf:
            zf.testzip()
            workbook_xml = zf.read("xl/workbook.xml")
            tree = ET.fromstring(workbook_xml)
            ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            sheet_names = {sheet.attrib["name"] for sheet in tree.findall(".//x:sheet", ns)}
            if sheet_names != expected_sheets:
                errors.append(f"Workbook sheets mismatch: {sorted(sheet_names)}")
            formula_count = 0
            for name in zf.namelist():
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                    formula_count += zf.read(name).count(b"<f>")
            if formula_count < 20:
                errors.append(f"Workbook formula count is too low: {formula_count}")
    except Exception as exc:
        errors.append(f"Workbook validation failed: {exc}")


def main() -> int:
    errors: list[str] = []
    validate_files(errors)
    validate_fact_reconciliation(errors)
    validate_rankings(errors)
    validate_workbook(errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Validation passed: generated files, KPI reconciliation, rankings, and workbook structure are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
