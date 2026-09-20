# Power BI Build Guide

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
