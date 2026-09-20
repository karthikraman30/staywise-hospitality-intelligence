const state = { property: '', month: '', channel: '', segment: '' };
const $ = (selector) => document.querySelector(selector);
const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2 });
const fullCurrency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const percentage = (value) => `${(value * 100).toFixed(1)}%`;
const request = async (route, extras = {}) => {
  const query = new URLSearchParams({ ...state, ...extras });
  return fetch(`${route}?${query}`).then((response) => response.json());
};
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[char]));

function populate(select, items, mapper) {
  const first = select.innerHTML;
  select.innerHTML = first + items.map((item) => `<option value="${escapeHtml(mapper(item).value)}">${escapeHtml(mapper(item).label)}</option>`).join('');
}

function renderKpis(summary) {
  const cards = [
    ['Realized revenue', currency.format(summary.realized_revenue), 'good'], ['Lost revenue', currency.format(summary.lost_revenue), 'alert'],
    ['Cancellation rate', percentage(summary.cancellation_rate), 'alert'], ['Occupancy', percentage(summary.occupancy_rate), 'good'],
    ['ADR', fullCurrency.format(summary.adr), ''], ['RevPAR', fullCurrency.format(summary.revpar), ''], ['Net RevPAR', fullCurrency.format(summary.net_revpar), 'good'],
  ];
  $('#kpis').innerHTML = cards.map(([label, value, tone]) => `<article class="kpi ${tone}"><small>${label}</small><strong>${value}</strong></article>`).join('');
}

function renderTrend(rows) {
  if (!rows.length) { $('#trend-chart').innerHTML = '<p class="empty">No bookings match the selected filters.</p>'; return; }
  const width = 760, height = 280, left = 48, right = 12, top = 16, bottom = 38;
  const max = Math.max(...rows.flatMap((row) => [row.realized_revenue, row.lost_revenue]), 1);
  const point = (index, value) => [left + (index / Math.max(rows.length - 1, 1)) * (width - left - right), top + (height - top - bottom) * (1 - value / max)];
  const polyline = (key) => rows.map((row, index) => point(index, row[key]).join(',')).join(' ');
  const grid = [0, .5, 1].map((fraction) => { const y = top + (height - top - bottom) * (1 - fraction); return `<line x1="${left}" x2="${width-right}" y1="${y}" y2="${y}" stroke="#e4e9e2"/><text x="${left-7}" y="${y+4}" text-anchor="end" font-size="9" fill="#61716d">$${(max*fraction/1e6).toFixed(1)}M</text>`; }).join('');
  const labels = rows.map((row, index) => (index % Math.ceil(rows.length / 6) === 0 || index === rows.length - 1) ? `<text x="${point(index, 0)[0]}" y="${height-12}" text-anchor="middle" font-size="9" fill="#61716d">${row.month.slice(2)}</text>` : '').join('');
  $('#trend-chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Monthly realized and lost revenue"><g>${grid}</g><polyline points="${polyline('realized_revenue')}" fill="none" stroke="#0e8f76" stroke-width="3"/><polyline points="${polyline('lost_revenue')}" fill="none" stroke="#e35d44" stroke-width="3"/>${labels}</svg>`;
}

function renderBars(target, rows, label, value, formatter, tone = '') {
  const limited = rows.slice(0, 6); const max = Math.max(...limited.map(value), 1);
  $(target).innerHTML = limited.length ? limited.map((row) => `<div class="bar-row"><span>${escapeHtml(label(row))}</span><div class="bar-track"><div class="bar ${tone}" style="width:${(value(row) / max) * 100}%"></div></div><span class="bar-value">${formatter(value(row))}</span></div>`).join('') : '<p class="empty">No matching data.</p>';
}

function renderAction(opportunities) {
  const top = opportunities[0];
  if (!top) { $('#priority-callout').textContent = 'No priority opportunity meets the 120-booking threshold for this filter selection.'; $('#action-summary').innerHTML = ''; return; }
  $('#priority-callout').innerHTML = `<strong>${escapeHtml(top.market_segment)} · ${escapeHtml(top.distribution_channel)} · ${escapeHtml(top.lead_time_band)}</strong><span>Rank #1 opportunity with ${fullCurrency.format(top.estimated_recoverable_revenue)} estimated recoverable revenue.</span>`;
  $('#action-summary').innerHTML = `<strong>${escapeHtml(top.recommended_intervention)}</strong><p>Start with ${escapeHtml(top.property_name)}. This segment has a ${percentage(top.cancellation_rate)} cancellation rate across ${top.bookings.toLocaleString()} bookings.</p><div class="action-metric"><span>Estimated recoverable revenue</span><b>${fullCurrency.format(top.estimated_recoverable_revenue)}</b></div><div class="action-metric"><span>Monitor</span><b>Cancellation rate · Net RevPAR</b></div>`;
}

function renderOpportunities(rows) {
  $('#opportunity-table').innerHTML = rows.slice(0, 8).map((row) => `<tr><td>#${row.priority_rank}</td><td>${escapeHtml(row.market_segment)}<br><small>${escapeHtml(row.property_name)}</small></td><td>${escapeHtml(row.distribution_channel)}</td><td>${escapeHtml(row.lead_time_band)}</td><td>${percentage(row.cancellation_rate)}</td><td>${fullCurrency.format(row.estimated_recoverable_revenue)}</td><td>${escapeHtml(row.recommended_intervention)}</td></tr>`).join('') || '<tr><td colspan="7" class="empty">No opportunity meets the minimum volume threshold.</td></tr>';
}

function renderRisk(rows) {
  $('#risk-table').innerHTML = rows.map((row) => `<div class="risk-row"><strong>${escapeHtml(row.risk_band)}</strong><span>${Number(row.bookings).toLocaleString()} bookings</span><span>${percentage(row.actual_cancellation_rate)} cancel rate</span></div>`).join('');
}

function scenarioSettings() {
  return { cancellation_reduction: Number($('#cancel-input').value) / 100, adr_uplift: Number($('#adr-input').value) / 100, occupancy_uplift: Number($('#occupancy-input').value) / 100, channel_mix: Number($('#mix-input').value) / 100 };
}
async function renderScenario() {
  const settings = scenarioSettings();
  $('#cancel-output').textContent = percentage(settings.cancellation_reduction); $('#adr-output').textContent = percentage(settings.adr_uplift); $('#occupancy-output').textContent = percentage(settings.occupancy_uplift); $('#mix-output').textContent = percentage(settings.channel_mix);
  const result = await request('/api/scenario', settings);
  $('#scenario-results').innerHTML = `<div><small>Incremental revenue</small><strong>${fullCurrency.format(result.total_incremental_revenue)}</strong></div><div><small>New realized revenue</small><strong>${currency.format(result.new_revenue)}</strong></div><div><small>Revenue lift</small><strong>${percentage(result.revenue_lift)}</strong></div>`;
}

async function refresh() {
  const [summary, monthly, drivers, channels, opportunities] = await Promise.all([request('/api/summary'), request('/api/monthly'), request('/api/drivers'), request('/api/channels'), request('/api/opportunities')]);
  renderKpis(summary); renderTrend(monthly); renderAction(opportunities); renderOpportunities(opportunities);
  renderBars('#driver-chart', drivers.filter((row) => row.bookings >= 500), (row) => `${row.driver_type}: ${row.driver_value}`, (row) => row.cancellation_rate, percentage, 'alert');
  renderBars('#channel-chart', channels, (row) => row.channel, (row) => row.net_revenue, currency);
  renderScenario();
}

async function init() {
  const filters = await request('/api/filters');
  populate($('#property'), filters.properties, (item) => ({ value:item.id, label:item.name })); populate($('#month'), filters.months, (item) => ({ value:item, label:item })); populate($('#channel'), filters.channels, (item) => ({ value:item, label:item })); populate($('#segment'), filters.segments, (item) => ({ value:item, label:item }));
  document.querySelectorAll('select').forEach((select) => select.addEventListener('change', () => { state[select.id] = select.value; refresh(); }));
  document.querySelectorAll('.scenario-controls input').forEach((input) => input.addEventListener('input', renderScenario));
  $('#reset').addEventListener('click', () => { Object.keys(state).forEach((key) => { state[key] = ''; $(`#${key}`).value = ''; }); refresh(); });
  renderRisk(await request('/api/risk')); refresh();
}
init().catch((error) => { document.body.innerHTML = `<main><h1>Dashboard unavailable</h1><p>${escapeHtml(error.message)}</p><p>Run <code>make build</code>, then <code>make demo</code>.</p></main>`; });
