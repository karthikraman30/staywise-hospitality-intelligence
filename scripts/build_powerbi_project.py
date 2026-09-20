#!/usr/bin/env python3
"""Generate a Power BI Project scaffold for StayWise.

This does not create a .pbix file. Microsoft Power BI Desktop is required to
open the generated .pbip project, refresh the model, build/verify visuals, and
save the final .pbix.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POWERBI = ROOT / "powerbi"
PROJECT = POWERBI / "StayWise_PowerBI_Project"
PROJECT_NAME = "StayWise"
REPORT_DIR = PROJECT / f"{PROJECT_NAME}.Report"
MODEL_DIR = PROJECT / f"{PROJECT_NAME}.SemanticModel"

TABLES = {
    "fact_bookings": "data/processed/fact_bookings.csv",
    "fact_daily_inventory": "data/processed/fact_daily_inventory.csv",
    "dim_date": "data/processed/dim_date.csv",
    "dim_property": "data/processed/dim_property.csv",
    "dim_channel": "data/processed/dim_channel.csv",
    "dim_market_segment": "data/processed/dim_market_segment.csv",
    "dim_customer": "data/processed/dim_customer.csv",
    "dim_room_type": "data/processed/dim_room_type.csv",
    "dim_country": "data/processed/dim_country.csv",
    "fact_monthly_targets": "data/processed/fact_monthly_targets.csv",
    "fact_local_events": "data/processed/fact_local_events.csv",
    "monthly_kpi_summary": "data/processed/monthly_kpi_summary.csv",
    "channel_profitability": "data/processed/channel_profitability.csv",
    "segment_opportunity_rankings": "outputs/segment_opportunity_rankings.csv",
    "cancellation_driver_analysis": "outputs/cancellation_driver_analysis.csv",
    "model_feature_importance": "outputs/model_feature_importance.csv",
    "cancellation_risk_segments": "outputs/cancellation_risk_segments.csv",
}

RELATIONSHIPS = [
    ("fact_bookings", "date_id", "dim_date", "date_id"),
    ("fact_bookings", "property_id", "dim_property", "property_id"),
    ("fact_bookings", "channel_id", "dim_channel", "channel_id"),
    ("fact_bookings", "market_segment_id", "dim_market_segment", "market_segment_id"),
    ("fact_bookings", "customer_type_id", "dim_customer", "customer_type_id"),
    ("fact_bookings", "room_type_id", "dim_room_type", "room_type_id"),
    ("fact_bookings", "country_id", "dim_country", "country_id"),
    ("fact_daily_inventory", "date_id", "dim_date", "date_id"),
    ("fact_daily_inventory", "property_id", "dim_property", "property_id"),
]

MEASURES = [
    ("Total Bookings", "COUNTROWS('fact_bookings')", "#,0"),
    ("Cancellations", "SUM('fact_bookings'[is_canceled])", "#,0"),
    ("Cancellation Rate", "DIVIDE([Cancellations], [Total Bookings])", "0.00%"),
    ("Potential Revenue", "SUM('fact_bookings'[potential_revenue])", "$#,0"),
    ("Realized Revenue", "SUM('fact_bookings'[realized_revenue])", "$#,0"),
    ("Lost Revenue", "SUM('fact_bookings'[lost_revenue])", "$#,0"),
    ("Cancellation Fee Revenue", "SUM('fact_bookings'[cancellation_fee_revenue])", "$#,0"),
    ("Commission Cost", "SUM('fact_bookings'[commission_cost])", "$#,0"),
    ("Net Revenue", "[Realized Revenue] - [Commission Cost]", "$#,0"),
    ("Room Nights Realized", "SUM('fact_bookings'[room_nights_realized])", "#,0"),
    ("Available Room Nights", "SUM('fact_daily_inventory'[available_room_nights])", "#,0"),
    ("Occupancy Rate", "DIVIDE([Room Nights Realized], [Available Room Nights])", "0.00%"),
    ("ADR", "DIVIDE([Realized Revenue], [Room Nights Realized])", "$#,0.00"),
    ("RevPAR", "DIVIDE([Realized Revenue], [Available Room Nights])", "$#,0.00"),
    ("Net RevPAR", "DIVIDE([Net Revenue], [Available Room Nights])", "$#,0.00"),
    (
        "Revenue Opportunity",
        "SUM('segment_opportunity_rankings'[estimated_recoverable_revenue])",
        "$#,0",
    ),
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INTEGER_NAME_HINTS = {"year", "month_number", "bookings", "cancellations", "rank", "nights", "guests", "count"}
DECIMAL_NAME_HINTS = {
    "adr",
    "amount",
    "cost",
    "fee",
    "index",
    "margin",
    "occupancy",
    "par",
    "percent",
    "rate",
    "revenue",
    "score",
    "share",
    "uplift",
}


def read_sample(relative_path: str, limit: int = 500) -> tuple[list[str], list[dict[str, str]]]:
    path = ROOT / relative_path
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for index, row in enumerate(reader):
            if index >= limit:
                break
            rows.append(row)
        return reader.fieldnames or [], rows


def infer_type(column: str, rows: list[dict[str, str]]) -> tuple[str, str]:
    values = [row.get(column, "") for row in rows if row.get(column, "") not in ("", None)]
    lowered = column.lower()
    if values and all(DATE_RE.match(value) for value in values):
        return "dateTime", "type date"
    if any(hint in lowered for hint in DECIMAL_NAME_HINTS):
        return "double", "type number"

    int_like = True
    float_like = True
    for value in values:
        try:
            number = float(value)
        except ValueError:
            int_like = False
            float_like = False
            break
        if not number.is_integer():
            int_like = False

    if values and int_like and (lowered == "date_id" or any(hint in lowered for hint in INTEGER_NAME_HINTS)):
        return "int64", "Int64.Type"
    if values and float_like:
        return "double", "type number"
    return "string", "type text"


def m_quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def m_expression(relative_path: str, columns: list[tuple[str, str, str]]) -> list[str]:
    type_pairs = ", ".join(f"{{{m_quote(name)}, {m_type}}}" for name, _, m_type in columns)
    return [
        "let",
        f"    Source = Csv.Document(File.Contents(ProjectRoot & {m_quote('/' + relative_path)}), [Delimiter=\",\", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),",
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
        f'    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{type_pairs}}})',
        "in",
        '    #"Changed Type"',
    ]


def build_table(table_name: str, relative_path: str) -> dict:
    headers, rows = read_sample(relative_path)
    typed_columns = [(header, *infer_type(header, rows)) for header in headers]
    columns = []
    for name, data_type, _ in typed_columns:
        summarize_by = "sum" if data_type in ("int64", "double") and not name.endswith("_id") else "none"
        columns.append(
            {
                "name": name,
                "dataType": data_type,
                "sourceColumn": name,
                "summarizeBy": summarize_by,
            }
        )

    table = {
        "name": table_name,
        "columns": columns,
        "partitions": [
            {
                "name": table_name,
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": m_expression(relative_path, typed_columns),
                },
            }
        ],
    }

    if table_name == "fact_bookings":
        table["measures"] = [
            {"name": name, "expression": expression, "formatString": fmt}
            for name, expression, fmt in MEASURES
        ]
    return table


def build_model() -> dict:
    tables = [build_table(table, path) for table, path in TABLES.items()]
    relationships = [
        {
            "name": f"{from_table}_{from_column}_to_{to_table}_{to_column}",
            "fromTable": from_table,
            "fromColumn": from_column,
            "toTable": to_table,
            "toColumn": to_column,
            "cardinality": "manyToOne",
            "crossFilteringBehavior": "oneDirection",
        }
        for from_table, from_column, to_table, to_column in RELATIONSHIPS
    ]

    return {
        "name": PROJECT_NAME,
        "compatibilityLevel": 1600,
        "model": {
            "culture": "en-US",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "expressions": [
                {
                    "name": "ProjectRoot",
                    "kind": "m",
                    "expression": m_quote(str(ROOT).replace("\\", "/")),
                }
            ],
            "tables": tables,
            "relationships": relationships,
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_project_files() -> None:
    write_json(
        PROJECT / f"{PROJECT_NAME}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{PROJECT_NAME}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    write_text(PROJECT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    write_json(
        REPORT_DIR / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{PROJECT_NAME}.SemanticModel"}},
        },
    )
    write_json(
        MODEL_DIR / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "1.0",
            "settings": {"qnaEnabled": True},
        },
    )
    write_json(MODEL_DIR / "model.bim", build_model())


def write_supporting_docs() -> None:
    dax_lines = [f"{name} = {expression}\n-- Format: {fmt}\n" for name, expression, fmt in MEASURES]
    write_text(POWERBI / "StayWise_DAX_Measures.dax", "\n".join(dax_lines))

    query_sections = []
    for table, relative_path in TABLES.items():
        headers, rows = read_sample(relative_path)
        typed_columns = [(header, *infer_type(header, rows)) for header in headers]
        query_sections.append(
            f"// Query: {table}\n"
            + "\n".join(m_expression(relative_path, typed_columns))
            + "\n"
        )
    write_text(POWERBI / "PowerQuery_Loads.pq", "\n\n".join(query_sections))

    checklist = """# StayWise PBIX Build Checklist

## Goal

Create `powerbi/StayWise_Dashboard.pbix` in Power BI Desktop.

## Fastest Path

1. Open Power BI Desktop on Windows.
2. Open `powerbi/StayWise_PowerBI_Project/StayWise.pbip`.
3. If Power BI asks for data source credentials, choose anonymous/file access.
4. If the project path differs from this machine, open Power Query and update the `ProjectRoot` query to the repository root.
5. Refresh the model.
6. Build the pages below.
7. Save as `powerbi/StayWise_Dashboard.pbix`.

## Required Pages

### Page 1: Executive Overview

- KPI cards: `Realized Revenue`, `Lost Revenue`, `Cancellation Rate`, `Occupancy Rate`, `ADR`, `RevPAR`, `Net RevPAR`.
- Line chart: `monthly_kpi_summary[year_month]` vs `monthly_kpi_summary[realized_revenue]` and `monthly_kpi_summary[lost_revenue]`.
- Bar chart: `segment_opportunity_rankings[estimated_recoverable_revenue]` by `opportunity_id` or segment label.
- Slicers: property, year-month, distribution channel, market segment.

### Page 2: Revenue Diagnostics

- Line chart: realized revenue by month and property.
- Clustered bar chart: net revenue by property and channel.
- Table: monthly KPI summary with bookings, cancellation rate, ADR, RevPAR, net RevPAR.

### Page 3: Cancellation Root Cause

- Bar charts: cancellation rate by lead-time band, channel, market segment, and deposit type.
- Table: `model_feature_importance`.
- Table: `cancellation_risk_segments`.

### Page 4: Channel Profitability

- Bar chart: realized revenue vs net revenue by channel.
- Bar chart: commission cost by channel.
- Table: channel profitability by property and channel.

### Page 5: Scenario Planner

- Import or reference `excel/StayWise_Scenario_Model.xlsx`.
- Show conservative, expected, and aggressive revenue scenarios.

### Page 6: Action Tracker

- Table: `segment_opportunity_rankings`.
- Include rank, property, segment, channel, lead-time band, cancellation rate, recoverable revenue, and recommended intervention.

## Demo Validation

Before the interview, confirm the dashboard cards match:

- Bookings: 119,390
- Cancellation rate: 37.04%
- Realized revenue: about $29.06M
- Lost revenue: about $13.66M
- Net revenue: about $24.68M
- Top opportunity: Resort Hotel | Online TA | TA/TO | 181+ days
"""
    write_text(POWERBI / "StayWise_PBIX_Build_Checklist.md", checklist)

    readme = """# StayWise Power BI Project

This folder is a generated Power BI Project scaffold for StayWise.

It is intended to be opened with Power BI Desktop on Windows and saved as:

`powerbi/StayWise_Dashboard.pbix`

The scaffold includes:

- `StayWise.pbip`
- Report pointer: `StayWise.Report/definition.pbir`
- Semantic model: `StayWise.SemanticModel/model.bim`
- CSV import queries for the project datasets
- Star-schema relationships
- DAX measures

Power BI Desktop is still required to refresh the model, verify the visuals, and save the final `.pbix`.
"""
    write_text(PROJECT / "README.md", readme)


def main() -> None:
    write_project_files()
    write_supporting_docs()
    print(f"Generated Power BI project scaffold at {PROJECT}")
    print("Open StayWise.pbip in Power BI Desktop on Windows, refresh, build visuals, and save as StayWise_Dashboard.pbix.")


if __name__ == "__main__":
    main()
