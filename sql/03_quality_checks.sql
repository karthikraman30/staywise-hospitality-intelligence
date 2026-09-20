SET search_path = staywise;

-- Row-count controls
SELECT 'fact_bookings' AS check_name, COUNT(*) AS row_count FROM fact_bookings
UNION ALL SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL SELECT 'dim_property', COUNT(*) FROM dim_property
UNION ALL SELECT 'dim_channel', COUNT(*) FROM dim_channel
UNION ALL SELECT 'fact_daily_inventory', COUNT(*) FROM fact_daily_inventory;

-- Duplicate booking IDs should return zero rows.
SELECT booking_id, COUNT(*) AS duplicate_count
FROM fact_bookings
GROUP BY booking_id
HAVING COUNT(*) > 1;

-- Revenue logic exceptions should return zero rows.
SELECT booking_id, is_canceled, potential_revenue, realized_revenue, lost_revenue, cancellation_fee_revenue
FROM fact_bookings
WHERE potential_revenue < 0
   OR realized_revenue < 0
   OR lost_revenue < 0
   OR cancellation_fee_revenue < 0
   OR (is_canceled = 1 AND realized_revenue <> cancellation_fee_revenue)
   OR (is_canceled = 0 AND lost_revenue <> 0);

-- Date consistency exceptions should return zero rows.
SELECT booking_id, arrival_date, date_id
FROM fact_bookings
WHERE to_char(arrival_date, 'YYYYMMDD')::integer <> date_id;

-- Orphan foreign keys should return zero rows.
SELECT b.booking_id, 'missing property' AS issue
FROM fact_bookings b
LEFT JOIN dim_property p ON b.property_id = p.property_id
WHERE p.property_id IS NULL
UNION ALL
SELECT b.booking_id, 'missing channel'
FROM fact_bookings b
LEFT JOIN dim_channel c ON b.channel_id = c.channel_id
WHERE c.channel_id IS NULL
UNION ALL
SELECT b.booking_id, 'missing date'
FROM fact_bookings b
LEFT JOIN dim_date d ON b.date_id = d.date_id
WHERE d.date_id IS NULL;

-- KPI reconciliation check.
SELECT
    ROUND(SUM(potential_revenue), 2) AS potential_revenue,
    ROUND(SUM(realized_revenue + lost_revenue), 2) AS realized_plus_lost,
    ROUND(SUM(potential_revenue) - SUM(realized_revenue + lost_revenue), 2) AS reconciliation_difference
FROM fact_bookings;
