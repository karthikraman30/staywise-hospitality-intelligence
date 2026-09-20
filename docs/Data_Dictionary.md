# Data Dictionary

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
