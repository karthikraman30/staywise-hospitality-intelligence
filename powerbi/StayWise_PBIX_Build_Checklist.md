# StayWise PBIX Build Checklist

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
