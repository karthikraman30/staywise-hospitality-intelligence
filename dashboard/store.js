// Browser-side port of DashboardStore in scripts/serve_dashboard.py.
// Works on the pre-aggregated cells in data.js so the dashboard runs with no server.
(function () {
  const raw = window.STAYWISE_DATA;
  if (!raw) return;

  const col = Object.fromEntries(raw.columns.map((name, index) => [name, index]));
  const cells = raw.cells.map((row) => Object.fromEntries(raw.columns.map((name, index) => [name, row[index]])));
  const inventory = raw.inventory.map(([property_id, month, available]) => ({ property_id, month, available }));
  const propertyNames = raw.property_names;

  const filteredCells = (p) => cells.filter((c) =>
    (!p.property || c.property_id === p.property) && (!p.month || c.arrival_year_month === p.month) &&
    (!p.channel || c.distribution_channel === p.channel) && (!p.segment || c.market_segment === p.segment));
  const availableNights = (p) => inventory.filter((i) => (!p.property || i.property_id === p.property) && (!p.month || i.month === p.month)).reduce((sum, i) => sum + i.available, 0);
  const add = (bucket, c, fields) => { for (const f of fields) bucket[f] = (bucket[f] || 0) + c[f]; };
  const round2 = (v) => Math.round(v * 100) / 100;

  function filters() {
    const uniq = (key) => [...new Set(cells.map((c) => c[key]))].sort();
    return { properties: Object.entries(propertyNames).map(([id, name]) => ({ id, name })), months: uniq('arrival_year_month'), channels: uniq('distribution_channel'), segments: uniq('market_segment') };
  }

  function summary(p) {
    const v = {};
    for (const c of filteredCells(p)) add(v, c, ['bookings', 'cancellations', 'potential_revenue', 'realized_revenue', 'lost_revenue', 'commission_cost', 'net_revenue', 'room_nights_realized']);
    const available = availableNights(p), realized = v.realized_revenue || 0, nights = v.room_nights_realized || 0;
    return {
      bookings: v.bookings || 0, cancellations: v.cancellations || 0, cancellation_rate: v.bookings ? v.cancellations / v.bookings : 0,
      potential_revenue: round2(v.potential_revenue || 0), realized_revenue: round2(realized), lost_revenue: round2(v.lost_revenue || 0),
      commission_cost: round2(v.commission_cost || 0), net_revenue: round2(v.net_revenue || 0), available_room_nights: available,
      occupancy_rate: available ? nights / available : 0, adr: nights ? realized / nights : 0, revpar: available ? realized / available : 0,
      net_revpar: available ? (v.net_revenue || 0) / available : 0,
    };
  }

  function monthly(p) {
    const grouped = {};
    for (const c of filteredCells(p)) add(grouped[c.arrival_year_month] ||= {}, c, ['bookings', 'realized_revenue', 'lost_revenue']);
    return Object.keys(grouped).sort().map((month) => ({
      month, bookings: grouped[month].bookings, realized_revenue: round2(grouped[month].realized_revenue), lost_revenue: round2(grouped[month].lost_revenue),
      available_room_nights: availableNights({ property: p.property, month }),
    }));
  }

  function drivers(p) {
    const labels = { lead_time_band: 'Lead time', distribution_channel: 'Channel', market_segment: 'Market segment', deposit_type: 'Deposit type' };
    const groups = {};
    for (const c of filteredCells(p)) for (const [field, label] of Object.entries(labels)) add(groups[`${label}\u0000${c[field]}`] ||= { driver_type: label, driver_value: c[field] }, c, ['bookings', 'cancellations', 'lost_revenue']);
    return Object.values(groups).map((g) => ({ driver_type: g.driver_type, driver_value: g.driver_value, bookings: g.bookings, cancellation_rate: g.bookings ? g.cancellations / g.bookings : 0, lost_revenue: round2(g.lost_revenue) }))
      .sort((a, b) => a.driver_type.localeCompare(b.driver_type) || b.cancellation_rate - a.cancellation_rate);
  }

  function channels(p) {
    const groups = {};
    for (const c of filteredCells(p)) add(groups[c.distribution_channel] ||= {}, c, ['bookings', 'cancellations', 'realized_revenue', 'commission_cost', 'net_revenue']);
    return Object.entries(groups).map(([channel, v]) => ({ channel, bookings: v.bookings, cancellation_rate: v.bookings ? v.cancellations / v.bookings : 0, realized_revenue: round2(v.realized_revenue), commission_cost: round2(v.commission_cost), net_revenue: round2(v.net_revenue) }))
      .sort((a, b) => b.net_revenue - a.net_revenue);
  }

  function opportunities(p) {
    const rows = filteredCells(p);
    const total = rows.reduce((s, c) => s + c.bookings, 0);
    const baseRate = total ? rows.reduce((s, c) => s + c.cancellations, 0) / total : 0;
    const groups = {};
    for (const c of rows) add(groups[[c.property_id, c.market_segment, c.distribution_channel, c.lead_time_band, c.deposit_type].join('\u0000')] ||= { property_id: c.property_id, market_segment: c.market_segment, distribution_channel: c.distribution_channel, lead_time_band: c.lead_time_band, deposit_type: c.deposit_type }, c, ['bookings', 'cancellations', 'lost_revenue']);
    const result = Object.values(groups).filter((g) => g.bookings >= 120).map((g) => {
      const rate = g.cancellations / g.bookings;
      const reduction = Math.min(0.35, Math.max(0.06, Math.max(rate - baseRate, 0) * 0.65));
      return {
        property_id: g.property_id, property_name: propertyNames[g.property_id], market_segment: g.market_segment, distribution_channel: g.distribution_channel,
        lead_time_band: g.lead_time_band, deposit_type: g.deposit_type, bookings: g.bookings, cancellation_rate: rate, lost_revenue: round2(g.lost_revenue),
        estimated_recoverable_revenue: round2(g.lost_revenue * reduction),
        recommended_intervention: ['91-180 days', '181+ days'].includes(g.lead_time_band) ? 'Pilot staged deposit or reconfirmation workflow' : 'Review channel and cancellation policy',
      };
    }).sort((a, b) => b.estimated_recoverable_revenue - a.estimated_recoverable_revenue);
    result.forEach((row, index) => { row.priority_rank = index + 1; });
    return result.slice(0, 15);
  }

  function scenario(p) {
    const s = summary(p);
    const assumption = (name) => Math.min(Math.max(Number(p[name]) || 0, 0), 0.5);
    const recovered = s.lost_revenue * assumption('cancellation_reduction'), adr = s.realized_revenue * assumption('adr_uplift');
    const occupancy = s.realized_revenue * assumption('occupancy_uplift'), savings = s.commission_cost * assumption('channel_mix');
    const total = recovered + adr + occupancy + savings;
    return { recovered_revenue: round2(recovered), adr_impact: round2(adr), occupancy_impact: round2(occupancy), channel_cost_savings: round2(savings), total_incremental_revenue: round2(total), new_revenue: round2(s.realized_revenue + total), revenue_lift: s.realized_revenue ? total / s.realized_revenue : 0 };
  }

  window.STAYWISE_STORE = { '/api/filters': filters, '/api/summary': summary, '/api/monthly': monthly, '/api/drivers': drivers, '/api/channels': channels, '/api/opportunities': opportunities, '/api/risk': () => raw.risk, '/api/scenario': scenario };
})();
