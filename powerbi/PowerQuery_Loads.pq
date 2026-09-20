// Query: fact_bookings
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/fact_bookings.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"booking_id", type text}, {"arrival_date", type date}, {"date_id", Int64.Type}, {"arrival_year_month", type text}, {"property_id", type text}, {"channel_id", type text}, {"market_segment_id", type text}, {"customer_type_id", type text}, {"room_type_id", type text}, {"country_id", type text}, {"hotel_source", type text}, {"distribution_channel", type text}, {"market_segment", type text}, {"customer_type", type text}, {"reserved_room_type", type text}, {"deposit_type", type text}, {"reservation_status", type text}, {"lead_time", type number}, {"lead_time_band", type text}, {"stay_nights", Int64.Type}, {"stay_band", type text}, {"guests", Int64.Type}, {"adr", type number}, {"is_canceled", type number}, {"potential_revenue", type number}, {"stay_revenue", type number}, {"realized_revenue", type number}, {"lost_revenue", type number}, {"deposit_recovery_rate", type number}, {"cancellation_fee_revenue", type number}, {"commission_rate", type number}, {"commission_cost", type number}, {"net_revenue", type number}, {"room_nights_booked", Int64.Type}, {"room_nights_realized", Int64.Type}, {"previous_cancellations", Int64.Type}, {"previous_cancel_band", type text}, {"total_special_requests", type number}, {"special_request_band", type text}, {"booking_changes", type number}, {"days_in_waiting_list", type number}, {"required_car_parking_spaces", type number}, {"room_mismatch_flag", type number}})
in
    #"Changed Type"


// Query: fact_daily_inventory
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/fact_daily_inventory.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"date_id", Int64.Type}, {"date", type date}, {"property_id", type text}, {"room_count", Int64.Type}, {"available_room_nights", Int64.Type}, {"source_type", type text}})
in
    #"Changed Type"


// Query: dim_date
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_date.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"date_id", Int64.Type}, {"date", type date}, {"year", Int64.Type}, {"month_number", Int64.Type}, {"month_name", type text}, {"quarter", type text}, {"year_month", type text}, {"day_of_week", type text}, {"is_weekend", type number}})
in
    #"Changed Type"


// Query: dim_property
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_property.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"property_id", type text}, {"property_name", type text}, {"property_type", type text}, {"city", type text}, {"country", type text}, {"room_count", Int64.Type}, {"target_adr", type number}, {"target_occupancy", type number}})
in
    #"Changed Type"


// Query: dim_channel
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_channel.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"channel_id", type text}, {"distribution_channel", type text}, {"channel_name", type text}, {"channel_group", type text}, {"commission_rate", type number}})
in
    #"Changed Type"


// Query: dim_market_segment
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_market_segment.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"market_segment_id", type text}, {"market_segment", type text}})
in
    #"Changed Type"


// Query: dim_customer
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_customer.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"customer_type_id", type text}, {"customer_type", type text}})
in
    #"Changed Type"


// Query: dim_room_type
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_room_type.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"room_type_id", type text}, {"room_type", type text}})
in
    #"Changed Type"


// Query: dim_country
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/dim_country.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"country_id", type text}, {"country_code", type text}, {"country_name", type text}})
in
    #"Changed Type"


// Query: fact_monthly_targets
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/fact_monthly_targets.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"target_id", type text}, {"year_month", type text}, {"property_id", type text}, {"target_occupancy", type number}, {"target_adr", type number}, {"target_cancellation_rate", type number}, {"source_type", type text}})
in
    #"Changed Type"


// Query: fact_local_events
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/fact_local_events.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"event_id", type text}, {"year_month", type text}, {"property_id", type text}, {"local_event_intensity_index", type number}, {"competitor_rate_index", type number}, {"source_type", type text}})
in
    #"Changed Type"


// Query: monthly_kpi_summary
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/monthly_kpi_summary.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"bookings", Int64.Type}, {"cancellations", Int64.Type}, {"cancellation_rate", type number}, {"potential_revenue", type number}, {"stay_revenue", type number}, {"realized_revenue", type number}, {"lost_revenue", type number}, {"cancellation_fee_revenue", type number}, {"room_nights_realized", Int64.Type}, {"room_nights_booked", Int64.Type}, {"adr", type number}, {"year_month", type text}, {"property_id", type text}, {"property_name", type text}, {"property_type", type text}, {"available_room_nights", Int64.Type}, {"occupancy_rate", type number}, {"revpar", type number}, {"net_revpar", type number}})
in
    #"Changed Type"


// Query: channel_profitability
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/data/processed/channel_profitability.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"bookings", Int64.Type}, {"cancellations", Int64.Type}, {"cancellation_rate", type number}, {"potential_revenue", type number}, {"stay_revenue", type number}, {"realized_revenue", type number}, {"lost_revenue", type number}, {"cancellation_fee_revenue", type number}, {"room_nights_realized", Int64.Type}, {"room_nights_booked", Int64.Type}, {"adr", type number}, {"property_id", type text}, {"property_name", type text}, {"property_type", type text}, {"distribution_channel", type text}, {"commission_rate", type number}, {"commission_cost", type number}, {"net_revenue", type number}, {"net_revenue_per_booking", type number}})
in
    #"Changed Type"


// Query: segment_opportunity_rankings
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/outputs/segment_opportunity_rankings.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"opportunity_id", type text}, {"property_id", type text}, {"property_source", type text}, {"market_segment", type text}, {"distribution_channel", type text}, {"lead_time_band", type text}, {"deposit_type", type text}, {"bookings", Int64.Type}, {"cancellations", Int64.Type}, {"cancellation_rate", type number}, {"lost_revenue", type number}, {"realized_revenue", type number}, {"commission_cost", type number}, {"achievable_cancellation_reduction", type number}, {"estimated_recoverable_revenue", type number}, {"recommended_intervention", type text}, {"priority_score", type number}, {"priority_rank", Int64.Type}})
in
    #"Changed Type"


// Query: cancellation_driver_analysis
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/outputs/cancellation_driver_analysis.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"driver_type", type text}, {"driver_value", type text}, {"bookings", Int64.Type}, {"cancellations", Int64.Type}, {"cancellation_rate", type number}, {"cancellation_rate_lift_vs_average", type number}, {"lost_revenue", type number}, {"realized_revenue", type number}})
in
    #"Changed Type"


// Query: model_feature_importance
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/outputs/model_feature_importance.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"feature", type text}, {"importance_score", type number}, {"business_interpretation", type text}, {"importance_share", type number}})
in
    #"Changed Type"


// Query: cancellation_risk_segments
let
    Source = Csv.Document(File.Contents(ProjectRoot & "/outputs/cancellation_risk_segments.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"risk_band", type text}, {"bookings", Int64.Type}, {"actual_cancellations", Int64.Type}, {"actual_cancellation_rate", type number}, {"average_predicted_risk", type number}, {"lost_revenue", type number}})
in
    #"Changed Type"
