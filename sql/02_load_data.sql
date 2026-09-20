-- Run from the repository root after `python3 scripts/build_staywise.py`.
-- Example:
--   createdb staywise
--   psql -d staywise -f sql/01_schema.sql
--   psql -d staywise -f sql/02_load_data.sql

SET search_path = staywise;

\copy dim_date FROM 'data/processed/dim_date.csv' WITH (FORMAT csv, HEADER true);
\copy dim_property FROM 'data/processed/dim_property.csv' WITH (FORMAT csv, HEADER true);
\copy dim_channel FROM 'data/processed/dim_channel.csv' WITH (FORMAT csv, HEADER true);
\copy dim_market_segment FROM 'data/processed/dim_market_segment.csv' WITH (FORMAT csv, HEADER true);
\copy dim_customer FROM 'data/processed/dim_customer.csv' WITH (FORMAT csv, HEADER true);
\copy dim_room_type FROM 'data/processed/dim_room_type.csv' WITH (FORMAT csv, HEADER true);
\copy dim_country FROM 'data/processed/dim_country.csv' WITH (FORMAT csv, HEADER true);
\copy dim_intervention_options FROM 'data/processed/dim_intervention_options.csv' WITH (FORMAT csv, HEADER true);
\copy fact_bookings FROM 'data/processed/fact_bookings.csv' WITH (FORMAT csv, HEADER true);
\copy fact_daily_inventory FROM 'data/processed/fact_daily_inventory.csv' WITH (FORMAT csv, HEADER true);
\copy fact_monthly_targets FROM 'data/processed/fact_monthly_targets.csv' WITH (FORMAT csv, HEADER true);
\copy fact_local_events FROM 'data/processed/fact_local_events.csv' WITH (FORMAT csv, HEADER true);
