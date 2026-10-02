/* SupportOps dashboard — camada visual sobre a API FastAPI.
   Sem dependências externas: gráficos em SVG são desenhados aqui. */

const API = '';
const STATUS_LABEL = {
  New: 'Novo',
  Assigned: 'Atribuído',
  'In Progress': 'Em andamento',
  Resolved: 'Resolvido',
  Closed: 'Fechado',
};
const SLA_LABEL = {
  met: 'Cumprido',
  breached: 'Violado',
  at_risk: 'Em risco',
  on_track: 'Em dia',
  no_policy: 'Sem política',
};
const STATE = { page: 1, pageSize: 20, total: 0, filters: {}, ticketCache: new Map() };

/* ------------------------------ helpers ------------------------------ */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = text; }
  if (!response.ok) {
    const detail = payload && payload.detail;
    throw new Error(formatDetail(detail) || `HTTP ${response.status}`);
  }
  return payload;
}

function formatDetail(detail) {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  }
  return JSON.stringify(detail);
}

const esc = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const num = (value) => (value === null || value === undefined ? '—' : value);
const hours = (value) => (value === null || value === undefined ? '—' : `${value} h`);

function fmtDate(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

function toast(message, kind = 'ok') {
  const el = $('#toast');
  el.textContent = message;
  el.className = `toast ${kind}`;
  el.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { el.hidden = true; }, 3600);
}

function badge(kind, label) {
  return `<span class="badge badge-${esc(kind)}">${esc(label)}</span>`;
}

/* ------------------------------ charts ------------------------------ */

function emptyChart(node, message) {
  node.innerHTML = `<p class="empty">${esc(message)}</p>`;
}

function horizontalBars(node, rows, { valueKey, labelKey, color = 'var(--accent)', suffix = '' }) {
  if (!rows || !rows.length) return emptyChart(node, 'Sem dados');
  const barH = 30, gap = 10, labelW = 110;
  const width = 460;
  const max = Math.max(...rows.map((r) => Number(r[valueKey]) || 0), 1);
  const height = rows.length * (barH + gap);
  const plotW = width - labelW - 60;

  const bars = rows.map((row, i) => {
    const raw = Number(row[valueKey]) || 0;
    const w = Math.max((raw / max) * plotW, 2);
    const y = i * (barH + gap);
    return `
      <text class="bar-label" x="${labelW - 8}" y="${y + barH / 2 + 4}" text-anchor="end">${esc(row[labelKey])}</text>
      <rect x="${labelW}" y="${y}" width="${w}" height="${barH}" rx="5" fill="${color}" opacity=".82"/>
      <text class="bar-value" x="${labelW + w + 8}" y="${y + barH / 2 + 4}">${raw}${suffix}</text>`;
  }).join('');

  node.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">${bars}</svg>`;
}

function groupedBars(node, rows) {
  if (!rows || !rows.length) return emptyChart(node, 'Sem dados');
  const width = 460, height = 220;
  const padL = 44, padB = 34, padT = 12;
  const plotW = width - padL - 12, plotH = height - padT - padB;
  const max = Math.max(...rows.flatMap((r) => [r.met, r.breached]), 1);
  const groupW = plotW / rows.length;
  const barW = Math.min(34, groupW / 2.6);

  const ticks = [0, 0.5, 1].map((ratio) => {
    const y = padT + plotH - ratio * plotH;
    return `<line class="grid-line" x1="${padL}" y1="${y}" x2="${width - 12}" y2="${y}"/>
            <text class="bar-value" x="${padL - 7}" y="${y + 4}" text-anchor="end">${Math.round(ratio * max)}</text>`;
  }).join('');

  const groups = rows.map((row, i) => {
    const base = padL + i * groupW + groupW / 2;
    const hMet = (row.met / max) * plotH;
    const hBad = (row.breached / max) * plotH;
    const y0 = padT + plotH;
    return `
      <rect x="${base - barW - 3}" y="${y0 - hMet}" width="${barW}" height="${Math.max(hMet, 1)}" rx="4" fill="var(--ok)" opacity=".85"/>
      <rect x="${base + 3}" y="${y0 - hBad}" width="${barW}" height="${Math.max(hBad, 1)}" rx="4" fill="var(--bad)" opacity=".85"/>
      <text class="bar-label" x="${base}" y="${height - 12}" text-anchor="middle">${esc(row.priority)}</text>
      <text class="bar-value" x="${base}" y="${height - 1}" text-anchor="middle">${row.compliance_rate_percent}%</text>`;
  }).join('');

  node.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">${ticks}${groups}</svg>`;
}

function lineChart(node, series) {
  const points = series.filter((p) => p.day);
  if (points.length < 2) return emptyChart(node, 'Dados insuficientes para a série temporal');
  const width = 620, height = 240;
  const padL = 40, padB = 30, padT = 12, padR = 10;
  const plotW = width - padL - padR, plotH = height - padT - padB;
  const max = Math.max(...points.flatMap((p) => [p.opened, p.resolved]), 1);
  const stepX = plotW / (points.length - 1);
  const x = (i) => padL + i * stepX;
  const y = (v) => padT + plotH - (v / max) * plotH;

  const path = (key) => points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join('');
  const area = `${path('opened')}L${x(points.length - 1).toFixed(1)},${padT + plotH}L${padL},${padT + plotH}Z`;

  const ticks = [0, 0.5, 1].map((ratio) => {
    const gy = padT + plotH - ratio * plotH;
    return `<line class="grid-line" x1="${padL}" y1="${gy}" x2="${width - padR}" y2="${gy}"/>
            <text class="bar-value" x="${padL - 7}" y="${gy + 4}" text-anchor="end">${Math.round(ratio * max)}</text>`;
  }).join('');

  // Rotula no máximo 6 pontos do eixo X para não sobrepor.
  const every = Math.max(1, Math.ceil(points.length / 6));
  const xLabels = points.map((p, i) =>
    i % every === 0 || i === points.length - 1
      ? `<text class="bar-value" x="${x(i)}" y="${height - 10}" text-anchor="middle">${p.day.slice(5)}</text>`
      : '').join('');

  node.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img">
    <defs><linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#4f8cff" stop-opacity=".38"/>
      <stop offset="100%" stop-color="#4f8cff" stop-opacity="0"/>
    </linearGradient></defs>
    ${ticks}
    <path d="${area}" fill="url(#grad)"/>
    <path d="${path('opened')}" fill="none" stroke="var(--accent)" stroke-width="2"/>
    <path d="${path('resolved')}" fill="none" stroke="var(--ok)" stroke-width="2" stroke-dasharray="4 3"/>
    ${xLabels}
  </svg>
  <p class="hint"><span style="color:var(--accent)">— Abertos</span> &nbsp; <span style="color:var(--ok)">- - Resolvidos</span></p>`;
}

/* ------------------------------ dashboard ------------------------------ */

function renderKpis(overview) {
  const complianceClass =
    overview.compliance_rate_percent >= 90 ? 'ok'
      : overview.compliance_rate_percent >= 70 ? 'warn' : 'bad';

  const cards = [
    { label: 'Total de tickets', value: num(overview.total_volume), note: `${num(overview.open_volume)} em aberto` },
    { label: 'Conformidade SLA', value: `${overview.compliance_rate_percent}%`, note: `${num(overview.breached_tickets)} violados`, cls: complianceClass },
    { label: 'Tempo médio de resolução', value: hours(overview.avg_resolution_time_hrs), note: `mediana ${hours(overview.median_resolution_time_hrs)}` },
    { label: 'P90 de resolução', value: hours(overview.p90_resolution_time_hrs), note: 'cauda longa' },
    { label: 'Primeira resposta', value: hours(overview.avg_first_response_time_hrs), note: 'New → In Progress' },
    { label: 'Backlog vencido', value: num(overview.open_breached), note: 'SLA estourado em aberto', cls: overview.open_breached > 0 ? 'bad' : 'ok' },
  ];

  $('#kpi-grid').innerHTML = cards.map((c) => `
    <div class="kpi ${c.cls || ''}">
      <div class="kpi-label">${esc(c.label)}</div>
      <div class="kpi-value">${esc(c.value)}</div>
      <div class="kpi-note">${esc(c.note)}</div>
    </div>`).join('');
}

async function loadDashboard() {
  try {
    const [overview, category, sla, trend, agent, backlog] = await Promise.all([
      api('/analytics/overview'),
      api('/analytics/by-category'),
      api('/analytics/sla-compliance'),
      api('/analytics/trend'),
      api('/analytics/by-agent'),
      api('/analytics/backlog'),
    ]);

    renderKpis(overview);
    horizontalBars($('#chart-category'), category, { valueKey: 'tickets', labelKey: 'category' });
    groupedBars($('#chart-sla'), sla);
    lineChart($('#chart-trend'), trend);
    horizontalBars($('#chart-agent'), agent, {
      valueKey: 'tickets_handled', labelKey: 'agent', color: 'var(--ok)',
    });

    const worst = [...sla].sort((a, b) => a.compliance_rate_percent - b.compliance_rate_percent)[0];
    $('#sla-hint').textContent = worst
      ? `Menor conformidade: ${worst.priority} com ${worst.compliance_rate_percent}% (${worst.breached} de ${worst.resolved} violados).`
      : '';

    renderBacklog(backlog);
  } catch (err) {
    toast(`Falha ao carregar o dashboard: ${err.message}`, 'bad');
  }
}

function renderBacklog(backlog) {
  $('#backlog-count').textContent = backlog.open_count;
  const node = $('#backlog-list');
  if (!backlog.tickets || !backlog.tickets.length) {
    node.innerHTML = '<p class="empty">Nenhum ticket em aberto.</p>';
    return;
  }

  node.innerHTML = backlog.tickets.map((t) => {
    const remaining = t.remaining_hours;
    const late = remaining !== null && remaining < 0;
    const dueText = late
      ? `${Math.abs(Math.round(remaining))} h em atraso`
      : remaining !== null ? `${Math.round(remaining)} h restantes` : 'sem prazo';
    return `
      <div class="backlog-item is-${esc(t.sla_state)}">
        <div class="backlog-main">
          <div class="backlog-title">#${t.id} · ${esc(t.issue_type)}</div>
          <div class="backlog-meta">${esc(t.category || '—')} · ${esc(t.agent || 'sem agente')} · ${esc(STATUS_LABEL[t.status] || t.status)}</div>
        </div>
        <div class="backlog-due">
          ${badge(t.sla_state, SLA_LABEL[t.sla_state] || t.sla_state)}
          <div class="backlog-meta" style="margin-top:4px">${esc(dueText)}</div>
        </div>
        <button class="btn btn-sm" data-transition="${t.id}">Alterar</button>
      </div>`;
  }).join('');
}

/* ------------------------------ tickets ------------------------------ */

function currentQuery() {
  const params = new URLSearchParams();
  const f = STATE.filters;
  if (f.status) params.set('status', f.status);
  if (f.priority) params.set('priority', f.priority);
  if (f.sla_state) params.set('sla_state', f.sla_state);
  if (f.category_id) params.set('category_id', f.category_id);
  if (f.agent_id) params.set('agent_id', f.agent_id);
  if (f.search) params.set('search', f.search);
  params.set('page', STATE.page);
  params.set('page_size', STATE.pageSize);
  return params.toString();
}

async function loadTickets() {
  const tbody = $('#tickets-table tbody');
  tbody.innerHTML = '<tr><td colspan="8" class="empty">Carregando…</td></tr>';
  try {
    const data = await api(`/tickets/?${currentQuery()}`);
    STATE.total = data.total;

    if (!data.items.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="empty">Nenhum ticket encontrado.</td></tr>';
    } else {
      tbody.innerHTML = data.items.map((t) => `
        <tr>
          <td class="num">#${t.id}</td>
          <td>${esc(t.issue_type)}</td>
          <td>${esc(t.category)}</td>
          <td>${esc(t.agent || '—')}</td>
          <td>${badge(t.status.replace(/\s/g, '_'), STATUS_LABEL[t.status] || t.status)}</td>
          <td>${badge(t.sla_state, SLA_LABEL[t.sla_state] || t.sla_state)}</td>
          <td class="nowrap num">${fmtDate(t.date_opened)}</td>
          <td class="nowrap">
            <button class="btn btn-sm" data-detail="${t.id}">Detalhe</button>
            <button class="btn btn-sm" data-transition="${t.id}">Status</button>
          </td>
        </tr>`).join('');
    }

    const pages = Math.max(1, Math.ceil(data.total / STATE.pageSize));
    $('#page-info').textContent = `Página ${STATE.page} de ${pages} · ${data.total} tickets`;
    $('#page-prev').disabled = STATE.page <= 1;
    $('#page-next').disabled = STATE.page >= pages;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty">Erro: ${esc(err.message)}</td></tr>`;
  }
}

async function showDetail(id) {
  try {
    const ticket = await api(`/tickets/${id}`);
    const history = await api(`/tickets/${id}/history`);
    const sla = ticket.sla || {};

    $('#detail-panel').hidden = false;
    $('#ticket-detail').innerHTML = `
      <dl>
        <div class="detail-row"><dt>Título</dt><dd>${esc(ticket.issue_type)}</dd></div>
        <div class="detail-row"><dt>Status</dt><dd>${badge(ticket.status.replace(/\s/g, '_'), STATUS_LABEL[ticket.status] || ticket.status)}</dd></div>
        <div class="detail-row"><dt>Categoria</dt><dd>${esc(ticket.category?.name || '—')}</dd></div>
        <div class="detail-row"><dt>Agente</dt><dd>${esc(ticket.agent?.name || '—')}</dd></div>
        <div class="detail-row"><dt>Solicitante</dt><dd>${esc(ticket.customer?.name || '—')}</dd></div>
        <div class="detail-row"><dt>Prioridade</dt><dd>${esc(sla.priority || '—')}</dd></div>
        <div class="detail-row"><dt>Situação SLA</dt><dd>${badge(sla.sla_state || 'no_policy', SLA_LABEL[sla.sla_state] || '—')}</dd></div>
        <div class="detail-row"><dt>Prazo</dt><dd>${fmtDate(sla.sla_due_at)}</dd></div>
        <div class="detail-row"><dt>Aberto em</dt><dd>${fmtDate(ticket.date_opened)}</dd></div>
        <div class="detail-row"><dt>Resolvido em</dt><dd>${fmtDate(ticket.date_resolved)}</dd></div>
        <div class="detail-row"><dt>Tempo de resolução</dt><dd>${hours(ticket.resolution_time_hours)}</dd></div>
        ${ticket.description ? `<div class="detail-row"><dt>Descrição</dt><dd>${esc(ticket.description)}</dd></div>` : ''}
      </dl>
      <h2 style="margin-top:18px">Histórico</h2>
      <ul class="timeline">
        ${history.map((h) => `
          <li>${badge(h.status.replace(/\s/g, '_'), STATUS_LABEL[h.status] || h.status)}
            <time>${fmtDate(h.changed_at)}</time>
            ${h.note ? `<div class="hint">${esc(h.note)}</div>` : ''}
          </li>`).join('')}
      </ul>
      <div style="margin-top:16px"><button class="btn btn-primary" data-transition="${ticket.id}">Alterar status</button></div>`;
  } catch (err) {
    toast(`Erro ao carregar o ticket: ${err.message}`, 'bad');
  }
}

/* ------------------------------ modal ------------------------------ */

let modalTicketId = null;

async function openTransition(id) {
  modalTicketId = id;
  const feedback = $('#modal-feedback');
  feedback.textContent = '';
  feedback.className = 'feedback';

  try {
    const [ticket, info] = await Promise.all([
      api(`/tickets/${id}`),
      api(`/tickets/${id}/transitions`),
    ]);

    $('#modal-sub').textContent =
      `#${ticket.id} · ${ticket.issue_type} · atual: ${STATUS_LABEL[ticket.status] || ticket.status}`;

    const select = $('#modal-status');
    select.innerHTML = info.allowed.length
      ? info.allowed.map((s) => `<option value="${esc(s)}">${esc(STATUS_LABEL[s] || s)}</option>`).join('')
      : '<option value="">Nenhuma transição permitida</option>';
    select.disabled = !info.allowed.length;
    $('#modal-note').value = '';
    $('#modal').hidden = false;
  } catch (err) {
    toast(`Erro: ${err.message}`, 'bad');
  }
}

function closeModal() {
  $('#modal').hidden = true;
  modalTicketId = null;
}

async function confirmTransition() {
  const status = $('#modal-status').value;
  const note = $('#modal-note').value.trim();
  const feedback = $('#modal-feedback');
  if (!status) return;

  try {
    await api(`/tickets/${modalTicketId}`, {
      method: 'PATCH',
      body: JSON.stringify(note ? { status, note } : { status }),
    });
    closeModal();
    toast(`Ticket #${modalTicketId} movido para ${STATUS_LABEL[status] || status}`);
    refreshAll();
  } catch (err) {
    feedback.textContent = err.message;
    feedback.className = 'feedback bad';
  }
}

/* ------------------------------ forms ------------------------------ */

async function loadLookups() {
  const [categories, agents, customers] = await Promise.all([
    api('/categories'),
    api('/agents'),
    api('/customers'),
  ]);

  const opts = (items, labelKey = 'name') =>
    items.map((i) => `<option value="${i.id}">${esc(i[labelKey])}</option>`).join('');

  $('#form-category').innerHTML = opts(categories);
  $('#form-agent').innerHTML = '<option value="">Não atribuído</option>' + opts(agents);
  $('#form-customer').innerHTML = '<option value="">Não informado</option>' + opts(customers);
  $('#filter-category').innerHTML = '<option value="">Todas</option>' + opts(categories);
  $('#filter-agent').innerHTML = '<option value="">Todos</option>' + opts(agents);
}

async function submitTicket(event) {
  event.preventDefault();
  const form = event.target;
  const feedback = $('#form-feedback');
  const data = Object.fromEntries(new FormData(form).entries());

  for (const key of ['category_id', 'agent_id', 'customer_id', 'operating_system']) {
    if (!data[key]) delete data[key];
  }

  feedback.textContent = 'Registrando…';
  feedback.className = 'feedback';

  try {
    const ticket = await api('/tickets/', { method: 'POST', body: JSON.stringify(data) });
    const sla = ticket.sla || {};
    feedback.textContent = `Ticket #${ticket.id} criado · SLA ${SLA_LABEL[sla.sla_state] || sla.sla_state}`;
    feedback.className = 'feedback ok';
    form.reset();
    $('#form-agent').value = '';
    $('#form-customer').value = '';
    await showDetail(ticket.id);
    refreshAll();
  } catch (err) {
    feedback.textContent = err.message;
    feedback.className = 'feedback bad';
  }
}

/* ------------------------------ wiring ------------------------------ */

function switchView(name) {
  $$('.tab').forEach((t) => t.classList.toggle('is-active', t.dataset.view === name));
  $$('.view').forEach((v) => v.classList.toggle('is-active', v.id === `view-${name}`));
  if (name === 'dashboard') loadDashboard();
  if (name === 'tickets') loadTickets();
}

async function checkHealth() {
  try {
    const health = await api('/health');
    const up = health.database === 'up';
    $('#health-dot').className = `dot ${up ? 'dot-up' : 'dot-down'}`;
    $('#health-text').textContent = `API ${health.version} · banco ${up ? 'online' : 'offline'}`;
  } catch {
    $('#health-dot').className = 'dot dot-down';
    $('#health-text').textContent = 'API inacessível';
  }
}

function refreshAll() {
  loadDashboard();
  if ($('#view-tickets').classList.contains('is-active')) loadTickets();
}

document.addEventListener('DOMContentLoaded', () => {
  $$('.tab').forEach((tab) => tab.addEventListener('click', () => switchView(tab.dataset.view)));
  $('#refresh').addEventListener('click', () => { checkHealth(); refreshAll(); toast('Dados atualizados'); });
  $('#ticket-form').addEventListener('submit', submitTicket);

  $('#ticket-filters').addEventListener('submit', (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    STATE.filters = Object.fromEntries(Object.entries(data).filter(([, v]) => v));
    STATE.page = 1;
    loadTickets();
  });

  $('#page-prev').addEventListener('click', () => {
    if (STATE.page > 1) { STATE.page--; loadTickets(); }
  });
  $('#page-next').addEventListener('click', () => {
    STATE.page++; loadTickets();
  });

  // Ações delegadas (tabelas, backlog, detalhe)
  document.addEventListener('click', (event) => {
    const detail = event.target.closest('[data-detail]');
    if (detail) { switchView('novo'); showDetail(detail.dataset.detail); return; }

    const transition = event.target.closest('[data-transition]');
    if (transition) { openTransition(transition.dataset.transition); return; }

    if (event.target.closest('[data-close]')) closeModal();
  });

  $('#modal-confirm').addEventListener('click', confirmTransition);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !$('#modal').hidden) closeModal();
  });

  checkHealth();
  loadLookups().catch((err) => toast(`Falha ao carregar cadastros: ${err.message}`, 'bad'));
  loadDashboard();
  setInterval(checkHealth, 30000);
});