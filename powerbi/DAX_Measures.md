# Power BI DAX Measures

```DAX
Total Bookings = COUNTROWS(fact_bookings)

Cancellations = SUM(fact_bookings[is_canceled])

Cancellation Rate = DIVIDE([Cancellations], [Total Bookings])

Potential Revenue = SUM(fact_bookings[potential_revenue])

Realized Revenue = SUM(fact_bookings[realized_revenue])

Lost Revenue = SUM(fact_bookings[lost_revenue])

Cancellation Fee Revenue = SUM(fact_bookings[cancellation_fee_revenue])

Commission Cost = SUM(fact_bookings[commission_cost])

Net Revenue = [Realized Revenue] - [Commission Cost]

Room Nights Realized = SUM(fact_bookings[room_nights_realized])

Available Room Nights = SUM(fact_daily_inventory[available_room_nights])

Occupancy Rate = DIVIDE([Room Nights Realized], [Available Room Nights])

ADR = DIVIDE([Realized Revenue], [Room Nights Realized])

RevPAR = DIVIDE([Realized Revenue], [Available Room Nights])

Net RevPAR = DIVIDE([Net Revenue], [Available Room Nights])

Revenue Opportunity = SUM(segment_opportunity_rankings[estimated_recoverable_revenue])
```
