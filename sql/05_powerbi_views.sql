SET search_path = staywise;

CREATE OR REPLACE VIEW pbi_fact_bookings_enriched AS
SELECT
    b.*,
    d.year,
    d.month_number,
    d.month_name,
    d.quarter,
    d.day_of_week,
    p.property_name,
    p.property_type,
    p.city,
    c.channel_name,
    c.channel_group
FROM fact_bookings b
JOIN dim_date d ON b.date_id = d.date_id
JOIN dim_property p ON b.property_id = p.property_id
JOIN dim_channel c ON b.channel_id = c.channel_id;

CREATE OR REPLACE VIEW pbi_monthly_scorecard AS
SELECT
    m.*,
    t.target_occupancy,
    t.target_adr,
    t.target_cancellation_rate,
    e.local_event_intensity_index,
    e.competitor_rate_index
FROM vw_monthly_property_kpis m
LEFT JOIN fact_monthly_targets t
  ON m.property_id = t.property_id
 AND m.arrival_year_month = t.year_month
LEFT JOIN fact_local_events e
  ON m.property_id = e.property_id
 AND m.arrival_year_month = e.year_month;

CREATE OR REPLACE VIEW pbi_action_tracker AS
SELECT *
FROM vw_opportunity_rankings
ORDER BY priority_rank;
