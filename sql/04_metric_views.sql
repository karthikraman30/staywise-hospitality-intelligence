SET search_path = staywise;

CREATE OR REPLACE VIEW vw_executive_kpis AS
WITH inventory AS (
    SELECT SUM(available_room_nights) AS available_room_nights
    FROM fact_daily_inventory
)
SELECT
    COUNT(*) AS bookings,
    SUM(is_canceled) AS cancellations,
    SUM(is_canceled)::numeric / NULLIF(COUNT(*), 0) AS cancellation_rate,
    SUM(potential_revenue) AS potential_revenue,
    SUM(realized_revenue) AS realized_revenue,
    SUM(lost_revenue) AS lost_revenue,
    SUM(cancellation_fee_revenue) AS cancellation_fee_revenue,
    SUM(commission_cost) AS commission_cost,
    SUM(net_revenue) AS net_revenue,
    SUM(room_nights_realized) AS room_nights_realized,
    inventory.available_room_nights,
    SUM(realized_revenue) / NULLIF(SUM(room_nights_realized), 0) AS adr,
    SUM(room_nights_realized)::numeric / NULLIF(inventory.available_room_nights, 0) AS occupancy_rate,
    SUM(realized_revenue) / NULLIF(inventory.available_room_nights, 0) AS revpar,
    SUM(net_revenue) / NULLIF(inventory.available_room_nights, 0) AS net_revpar
FROM fact_bookings
CROSS JOIN inventory
GROUP BY inventory.available_room_nights;

CREATE OR REPLACE VIEW vw_monthly_property_kpis AS
WITH monthly_inventory AS (
    SELECT
        date_trunc('month', date)::date AS month_start,
        property_id,
        SUM(available_room_nights) AS available_room_nights
    FROM fact_daily_inventory
    GROUP BY 1, 2
)
SELECT
    b.arrival_year_month,
    b.property_id,
    p.property_name,
    p.property_type,
    COUNT(*) AS bookings,
    SUM(b.is_canceled) AS cancellations,
    SUM(b.is_canceled)::numeric / NULLIF(COUNT(*), 0) AS cancellation_rate,
    SUM(b.potential_revenue) AS potential_revenue,
    SUM(b.realized_revenue) AS realized_revenue,
    SUM(b.lost_revenue) AS lost_revenue,
    SUM(b.cancellation_fee_revenue) AS cancellation_fee_revenue,
    SUM(b.commission_cost) AS commission_cost,
    SUM(b.net_revenue) AS net_revenue,
    SUM(b.room_nights_realized) AS room_nights_realized,
    i.available_room_nights,
    SUM(b.realized_revenue) / NULLIF(SUM(b.room_nights_realized), 0) AS adr,
    SUM(b.room_nights_realized)::numeric / NULLIF(i.available_room_nights, 0) AS occupancy_rate,
    SUM(b.realized_revenue) / NULLIF(i.available_room_nights, 0) AS revpar,
    SUM(b.net_revenue) / NULLIF(i.available_room_nights, 0) AS net_revpar
FROM fact_bookings b
JOIN dim_property p ON b.property_id = p.property_id
JOIN monthly_inventory i
  ON b.property_id = i.property_id
 AND date_trunc('month', b.arrival_date)::date = i.month_start
GROUP BY b.arrival_year_month, b.property_id, p.property_name, p.property_type, i.available_room_nights;

CREATE OR REPLACE VIEW vw_channel_profitability AS
SELECT
    b.property_id,
    p.property_name,
    b.distribution_channel,
    c.channel_group,
    COUNT(*) AS bookings,
    SUM(b.is_canceled) AS cancellations,
    SUM(b.is_canceled)::numeric / NULLIF(COUNT(*), 0) AS cancellation_rate,
    SUM(b.realized_revenue) AS realized_revenue,
    SUM(b.commission_cost) AS commission_cost,
    SUM(b.net_revenue) AS net_revenue,
    SUM(b.net_revenue) / NULLIF(COUNT(*), 0) AS net_revenue_per_booking
FROM fact_bookings b
JOIN dim_property p ON b.property_id = p.property_id
JOIN dim_channel c ON b.channel_id = c.channel_id
GROUP BY b.property_id, p.property_name, b.distribution_channel, c.channel_group;

CREATE OR REPLACE VIEW vw_cancellation_drivers AS
SELECT 'Lead Time Band' AS driver_type, lead_time_band AS driver_value, COUNT(*) AS bookings, SUM(is_canceled) AS cancellations,
       SUM(is_canceled)::numeric / NULLIF(COUNT(*), 0) AS cancellation_rate, SUM(lost_revenue) AS lost_revenue
FROM fact_bookings GROUP BY lead_time_band
UNION ALL
SELECT 'Channel', distribution_channel, COUNT(*), SUM(is_canceled),
       SUM(is_canceled)::numeric / NULLIF(COUNT(*), 0), SUM(lost_revenue)
FROM fact_bookings GROUP BY distribution_channel
UNION ALL
SELECT 'Market Segment', market_segment, COUNT(*), SUM(is_canceled),
       SUM(is_canceled)::numeric / NULLIF(COUNT(*), 0), SUM(lost_revenue)
FROM fact_bookings GROUP BY market_segment
UNION ALL
SELECT 'Deposit Type', deposit_type, COUNT(*), SUM(is_canceled),
       SUM(is_canceled)::numeric / NULLIF(COUNT(*), 0), SUM(lost_revenue)
FROM fact_bookings GROUP BY deposit_type;

CREATE OR REPLACE VIEW vw_opportunity_rankings AS
WITH base AS (
    SELECT
        property_id,
        hotel_source,
        market_segment,
        distribution_channel,
        lead_time_band,
        deposit_type,
        COUNT(*) AS bookings,
        SUM(is_canceled) AS cancellations,
        SUM(is_canceled)::numeric / NULLIF(COUNT(*), 0) AS cancellation_rate,
        SUM(lost_revenue) AS lost_revenue,
        SUM(realized_revenue) AS realized_revenue,
        SUM(commission_cost) AS commission_cost
    FROM fact_bookings
    GROUP BY 1, 2, 3, 4, 5, 6
),
avg_rate AS (
    SELECT SUM(is_canceled)::numeric / COUNT(*) AS average_cancellation_rate
    FROM fact_bookings
)
SELECT
    ROW_NUMBER() OVER (
        ORDER BY
            lost_revenue * LEAST(0.35, GREATEST(0.06, GREATEST(cancellation_rate - average_cancellation_rate, 0) * 0.65)) DESC
    ) AS priority_rank,
    base.*,
    LEAST(0.35, GREATEST(0.06, GREATEST(cancellation_rate - average_cancellation_rate, 0) * 0.65)) AS achievable_cancellation_reduction,
    lost_revenue * LEAST(0.35, GREATEST(0.06, GREATEST(cancellation_rate - average_cancellation_rate, 0) * 0.65)) AS estimated_recoverable_revenue
FROM base
CROSS JOIN avg_rate
WHERE bookings >= 120;
