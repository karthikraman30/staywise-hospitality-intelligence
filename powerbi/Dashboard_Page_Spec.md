# Power BI Dashboard Page Specification

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
