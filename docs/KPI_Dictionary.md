# KPI Dictionary

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
