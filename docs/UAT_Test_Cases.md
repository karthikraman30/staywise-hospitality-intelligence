# UAT Test Cases

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
