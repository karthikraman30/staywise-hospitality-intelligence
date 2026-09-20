#!/usr/bin/env python3
"""Load StayWise processed data into a local SQLite database for instant querying."""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "staywise.db"

TABLE_FILES = {
    "dim_date": PROCESSED / "dim_date.csv",
    "dim_property": PROCESSED / "dim_property.csv",
    "dim_channel": PROCESSED / "dim_channel.csv",
    "dim_market_segment": PROCESSED / "dim_market_segment.csv",
    "dim_customer": PROCESSED / "dim_customer.csv",
    "dim_room_type": PROCESSED / "dim_room_type.csv",
    "dim_country": PROCESSED / "dim_country.csv",
    "dim_intervention_options": PROCESSED / "dim_intervention_options.csv",
    "fact_bookings": PROCESSED / "fact_bookings.csv",
    "fact_daily_inventory": PROCESSED / "fact_daily_inventory.csv",
    "fact_monthly_targets": PROCESSED / "fact_monthly_targets.csv",
    "fact_local_events": PROCESSED / "fact_local_events.csv",
    "monthly_kpi_summary": PROCESSED / "monthly_kpi_summary.csv",
    "channel_profitability": PROCESSED / "channel_profitability.csv",
}

def load_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")

    print(f"Creating database at {DB_PATH.name}...")

    for table_name, csv_path in TABLE_FILES.items():
        if not csv_path.exists():
            print(f"Skipping {table_name}, file not found.")
            continue
        
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            col_defs = ", ".join([f'"{h}" TEXT' for h in headers])
            cursor.execute(f'CREATE TABLE "{table_name}" ({col_defs});')
            
            placeholders = ", ".join(["?"] * len(headers))
            insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
            
            rows = list(reader)
            cursor.executemany(insert_sql, rows)
            print(f"  Loaded {table_name}: {len(rows):,} rows")

    # Create Core Views in SQLite
    cursor.execute("""
    CREATE VIEW vw_executive_kpis AS
    SELECT 
        COUNT(*) AS bookings,
        SUM(CAST(is_canceled AS INT)) AS cancellations,
        ROUND(CAST(SUM(CAST(is_canceled AS INT)) AS FLOAT) / COUNT(*), 4) AS cancellation_rate,
        ROUND(SUM(CAST(potential_revenue AS FLOAT)), 2) AS potential_revenue,
        ROUND(SUM(CAST(realized_revenue AS FLOAT)), 2) AS realized_revenue,
        ROUND(SUM(CAST(lost_revenue AS FLOAT)), 2) AS lost_revenue,
        ROUND(SUM(CAST(commission_cost AS FLOAT)), 2) AS commission_cost,
        ROUND(SUM(CAST(net_revenue AS FLOAT)), 2) AS net_revenue
    FROM fact_bookings;
    """)

    cursor.execute("""
    CREATE VIEW vw_channel_profitability AS
    SELECT 
        property_id,
        distribution_channel,
        COUNT(*) AS bookings,
        SUM(CAST(is_canceled AS INT)) AS cancellations,
        ROUND(CAST(SUM(CAST(is_canceled AS INT)) AS FLOAT) / COUNT(*), 4) AS cancellation_rate,
        ROUND(SUM(CAST(realized_revenue AS FLOAT)), 2) AS realized_revenue,
        ROUND(SUM(CAST(commission_cost AS FLOAT)), 2) AS commission_cost,
        ROUND(SUM(CAST(net_revenue AS FLOAT)), 2) AS net_revenue,
        ROUND(SUM(CAST(net_revenue AS FLOAT)) / COUNT(*), 2) AS net_revenue_per_booking
    FROM fact_bookings
    GROUP BY property_id, distribution_channel;
    """)

    cursor.execute("""
    CREATE VIEW vw_cancellation_drivers AS
    SELECT 'Lead Time Band' AS driver_type, lead_time_band AS driver_value, 
           COUNT(*) AS bookings, SUM(CAST(is_canceled AS INT)) AS cancellations,
           ROUND(CAST(SUM(CAST(is_canceled AS INT)) AS FLOAT) / COUNT(*), 4) AS cancellation_rate, 
           ROUND(SUM(CAST(lost_revenue AS FLOAT)), 2) AS lost_revenue
    FROM fact_bookings GROUP BY lead_time_band
    UNION ALL
    SELECT 'Channel', distribution_channel, COUNT(*), SUM(CAST(is_canceled AS INT)),
           ROUND(CAST(SUM(CAST(is_canceled AS INT)) AS FLOAT) / COUNT(*), 4), 
           ROUND(SUM(CAST(lost_revenue AS FLOAT)), 2)
    FROM fact_bookings GROUP BY distribution_channel
    UNION ALL
    SELECT 'Market Segment', market_segment, COUNT(*), SUM(CAST(is_canceled AS INT)),
           ROUND(CAST(SUM(CAST(is_canceled AS INT)) AS FLOAT) / COUNT(*), 4), 
           ROUND(SUM(CAST(lost_revenue AS FLOAT)), 2)
    FROM fact_bookings GROUP BY market_segment;
    """)

    conn.commit()
    conn.close()
    print(f"Database successfully built at {DB_PATH.name} with tables and views.")

if __name__ == "__main__":
    load_db()
