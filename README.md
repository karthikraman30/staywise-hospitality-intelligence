# StayWise — Hospitality Revenue & Decision Intelligence Platform

StayWise is a Business Analyst portfolio project that turns raw hotel booking records into a decision-support system for revenue leakage, cancellation risk, channel profitability, and intervention planning.

The project is intentionally built as more than a Power BI dashboard. It includes business requirements, KPI definitions, PostgreSQL schema design, data quality checks, SQL metric views, Python analysis, an Excel scenario model, and Power BI-ready datasets.

## Business Question

How can a hotel group recover avoidable revenue leakage from cancellations, underutilized inventory, and unprofitable channel mix?

## What Makes This Project Different

Most hospitality analytics projects stop at descriptive visuals. StayWise adds a decision layer:

- Converts booking-level records into stakeholder-ready KPIs such as realized revenue, lost revenue, occupancy, ADR, RevPAR, net RevPAR, cancellation leakage, and channel profitability.
- Uses segmentation and interpretable cancellation-risk scoring to identify where leakage is concentrated.
- Builds an Excel scenario model so a revenue manager can test ADR, cancellation, occupancy, and channel-mix interventions.
- Includes BA artifacts such as a BRD, stakeholder map, KPI dictionary, traceability matrix, UAT test cases, and executive recommendation memo.

## Data Source

The raw booking data comes from the public Hotel Booking Demand dataset, distributed through the R for Data Science TidyTuesday project:

`https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-02-11/hotels.csv`

The repository also creates synthetic business enrichment tables for channel commissions, inventory, monthly targets, competitor rate index, local event intensity, and intervention options. These tables are clearly labeled as synthetic and are used to make the project resemble a real BA decision-intelligence assignment.

## Project Structure

```text
data/
  raw/                  Raw public dataset
  processed/            Clean facts, dimensions, KPI extracts, Power BI-ready CSVs
docs/                   BA artifacts and executive recommendation memo
excel/                  Excel scenario model
notebooks/              Portfolio analysis notebook
outputs/                Charts and analytical summaries
powerbi/                Power BI build guide, DAX measures, page specification
scripts/                Reproducible project build script
sql/                    PostgreSQL schema, QA, metric views, and BI views
src/staywise/           Python package marker
```

## Quick Start

```sh
make all
```

This downloads the raw dataset, builds processed data, writes analytical outputs, creates the Excel scenario model, and refreshes generated documentation.

If `make` is unavailable:

```sh
python3 scripts/build_staywise.py
```

The build script uses only the Python standard library. `requirements.txt` is included for optional notebook/BI extension work.

Validate generated outputs:

```sh
make validate
```

## Mac Interview Demo

Run the local decision dashboard with no external services or browser plugins:

```sh
make demo
```

Open `http://127.0.0.1:8000`. The dashboard is backed by the generated booking fact table and supports filters, KPI diagnostics, scenario assumptions, and a ranked recovery backlog.

## PostgreSQL Workflow

With a local PostgreSQL server (set `PGUSER`/`PGPASSWORD` or use `~/.pgpass`; see `.env.example`):

```sh
make pg-create     # createdb staywise
make pg-load       # schema, \copy the CSVs, metric views, Power BI views
make pg-quality    # sql/03_quality_checks.sql - every exception query should return zero rows
make pg-validate   # reconcile PostgreSQL KPIs to the Python executive summary
```

Without a local server, the same steps run in Docker: `make db-up`, `make db-load`, `make db-quality`, `make db-validate`.

For instant SQL practice with no server at all, `make db-sqlite` loads the same star schema into `staywise.db` (SQLite).

The generated CSV files are also directly importable into Power BI.

## Analysis Notebook

`notebooks/StayWise_Analysis_Notebook.ipynb` reproduces the whole analysis in pandas/NumPy/matplotlib — data-quality gate, executive KPIs (asserted equal to the pipeline output), driver analysis, channel economics, the opportunity ranking (asserted equal to the pipeline's top 10), monthly trend, and a plain-language explanation of the risk score. Re-run it with `make notebook`.

## Final Deliverables

- Business requirements and stakeholder documentation in `docs/`
- PostgreSQL star schema and metric views in `sql/`
- Clean fact/dimension datasets in `data/processed/`
- Root-cause, segmentation, and opportunity outputs in `outputs/`
- Excel scenario model: `excel/StayWise_Scenario_Model.xlsx`
- Mac-ready decision dashboard: `dashboard/`, served by `make demo`
- Power BI project scaffold, implementation guide, DAX measures, and page spec in `powerbi/`

## Resume Version

**StayWise — Hospitality Revenue & Decision Intelligence Platform**  
PostgreSQL, SQL, Python, Excel, Power BI, DAX

- Built a self-directed, end-to-end revenue-leakage analysis on a public dataset of 119K+ hotel bookings, defining KPIs for realized revenue, lost revenue, occupancy, ADR, RevPAR, and cancellation rate to quantify where the business was losing money.
- Designed a PostgreSQL star schema and wrote SQL validation scripts to reconcile revenue and catch data-quality issues across property, customer segment, booking channel, lead-time band, and deposit type.
- Used Python for root-cause analysis to rank recovery opportunities, built an Excel scenario model to test intervention impact, and built a lightweight local dashboard (Python HTTP server, HTML/CSS/JS) with interactive filters and KPI diagnostics, alongside Power BI-ready DAX measures for handoff to a BI tool.

## Honest Scope Notes

- **Bookings are real; operating assumptions are synthetic.** The 119,390 reservations come from the public dataset. Channel commission rates, room inventory, deposit-recovery rates, targets and event indices are documented placeholders (see `docs/Data_Dictionary.md`) that a real hotel would replace with actuals.
- **The cancellation risk score is interpretable and rule-based, not a trained ML model.** It shifts the portfolio cancellation rate by each booking attribute's observed rate (see notebook section 8).
- **No `.pbix` file is committed.** Power BI Desktop is Windows-only and this project was built on macOS. The repo ships the semantic model (`.pbip` scaffold, relationships, DAX measures, page spec) needed to build the report in Power BI Desktop; the local HTML dashboard is the working demo.
- **Recoverable revenue is a prioritization estimate**, not measured impact. The recommendation is a scoped pilot with a control group and guardrail metrics.

## Interview Positioning

The hardest part of this project was not building a dashboard. It was converting raw booking records into validated decision metrics that stakeholders can trust. StayWise defines revenue leakage, cancellation impact, channel profitability, RevPAR, net RevPAR, and scenario assumptions, then reconciles those definitions across PostgreSQL, Python, Excel, the Mac decision dashboard, and Power BI-ready outputs.
