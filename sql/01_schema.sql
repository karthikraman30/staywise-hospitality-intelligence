DROP SCHEMA IF EXISTS staywise CASCADE;
CREATE SCHEMA staywise;
SET search_path = staywise;

CREATE TABLE dim_date (
    date_id integer PRIMARY KEY,
    date date NOT NULL,
    year integer NOT NULL,
    month_number integer NOT NULL,
    month_name text NOT NULL,
    quarter text NOT NULL,
    year_month text NOT NULL,
    day_of_week text NOT NULL,
    is_weekend integer NOT NULL CHECK (is_weekend IN (0, 1))
);

CREATE TABLE dim_property (
    property_id text PRIMARY KEY,
    property_name text NOT NULL,
    property_type text NOT NULL,
    city text NOT NULL,
    country text NOT NULL,
    room_count integer NOT NULL CHECK (room_count > 0),
    target_adr numeric(12,2) NOT NULL,
    target_occupancy numeric(8,4) NOT NULL
);

CREATE TABLE dim_channel (
    channel_id text PRIMARY KEY,
    distribution_channel text NOT NULL,
    channel_name text NOT NULL,
    channel_group text NOT NULL,
    commission_rate numeric(8,4) NOT NULL CHECK (commission_rate >= 0)
);

CREATE TABLE dim_market_segment (
    market_segment_id text PRIMARY KEY,
    market_segment text NOT NULL
);

CREATE TABLE dim_customer (
    customer_type_id text PRIMARY KEY,
    customer_type text NOT NULL
);

CREATE TABLE dim_room_type (
    room_type_id text PRIMARY KEY,
    room_type text NOT NULL
);

CREATE TABLE dim_country (
    country_id text PRIMARY KEY,
    country_code text NOT NULL,
    country_name text NOT NULL
);

CREATE TABLE dim_intervention_options (
    intervention_id text PRIMARY KEY,
    intervention_name text NOT NULL,
    primary_driver text NOT NULL,
    owner_role text NOT NULL,
    expected_kpi text NOT NULL,
    implementation_effort text NOT NULL
);

CREATE TABLE fact_bookings (
    booking_id text PRIMARY KEY,
    arrival_date date NOT NULL,
    date_id integer NOT NULL REFERENCES dim_date(date_id),
    arrival_year_month text NOT NULL,
    property_id text NOT NULL REFERENCES dim_property(property_id),
    channel_id text NOT NULL REFERENCES dim_channel(channel_id),
    market_segment_id text NOT NULL REFERENCES dim_market_segment(market_segment_id),
    customer_type_id text NOT NULL REFERENCES dim_customer(customer_type_id),
    room_type_id text NOT NULL REFERENCES dim_room_type(room_type_id),
    country_id text NOT NULL REFERENCES dim_country(country_id),
    hotel_source text NOT NULL,
    distribution_channel text NOT NULL,
    market_segment text NOT NULL,
    customer_type text NOT NULL,
    reserved_room_type text NOT NULL,
    deposit_type text NOT NULL,
    reservation_status text NOT NULL,
    lead_time integer NOT NULL,
    lead_time_band text NOT NULL,
    stay_nights integer NOT NULL,
    stay_band text NOT NULL,
    guests integer NOT NULL,
    adr numeric(12,2) NOT NULL,
    is_canceled integer NOT NULL CHECK (is_canceled IN (0, 1)),
    potential_revenue numeric(14,2) NOT NULL,
    stay_revenue numeric(14,2) NOT NULL,
    realized_revenue numeric(14,2) NOT NULL,
    lost_revenue numeric(14,2) NOT NULL,
    deposit_recovery_rate numeric(8,4) NOT NULL,
    cancellation_fee_revenue numeric(14,2) NOT NULL,
    commission_rate numeric(8,4) NOT NULL,
    commission_cost numeric(14,2) NOT NULL,
    net_revenue numeric(14,2) NOT NULL,
    room_nights_booked integer NOT NULL,
    room_nights_realized integer NOT NULL,
    previous_cancellations integer NOT NULL,
    previous_cancel_band text NOT NULL,
    total_special_requests integer NOT NULL,
    special_request_band text NOT NULL,
    booking_changes integer NOT NULL,
    days_in_waiting_list integer NOT NULL,
    required_car_parking_spaces integer NOT NULL,
    room_mismatch_flag integer NOT NULL CHECK (room_mismatch_flag IN (0, 1))
);

CREATE TABLE fact_daily_inventory (
    date_id integer NOT NULL REFERENCES dim_date(date_id),
    date date NOT NULL,
    property_id text NOT NULL REFERENCES dim_property(property_id),
    room_count integer NOT NULL,
    available_room_nights integer NOT NULL,
    source_type text NOT NULL,
    PRIMARY KEY (date_id, property_id)
);

CREATE TABLE fact_monthly_targets (
    target_id text PRIMARY KEY,
    year_month text NOT NULL,
    property_id text NOT NULL REFERENCES dim_property(property_id),
    target_occupancy numeric(8,4) NOT NULL,
    target_adr numeric(12,2) NOT NULL,
    target_cancellation_rate numeric(8,4) NOT NULL,
    source_type text NOT NULL
);

CREATE TABLE fact_local_events (
    event_id text PRIMARY KEY,
    year_month text NOT NULL,
    property_id text NOT NULL REFERENCES dim_property(property_id),
    local_event_intensity_index numeric(10,2) NOT NULL,
    competitor_rate_index numeric(10,3) NOT NULL,
    source_type text NOT NULL
);

CREATE INDEX idx_fact_bookings_arrival_date ON fact_bookings(arrival_date);
CREATE INDEX idx_fact_bookings_property_month ON fact_bookings(property_id, arrival_year_month);
CREATE INDEX idx_fact_bookings_channel ON fact_bookings(channel_id);
CREATE INDEX idx_fact_bookings_segment ON fact_bookings(market_segment_id);
