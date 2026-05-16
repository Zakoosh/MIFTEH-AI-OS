/* MIFTEH AI OS Dashboard — miftehos.com
 * GitHub-native architecture: reads from /data/dashboard.json (no backend required).
 * Auth: token-based session via localStorage, validated against /data/auth_config.json.
 */
'use strict';

const _DATA_URL = (typeof window.MIFTEH_DATA_URL !== 'undefined')
  ? window.MIFTEH_DATA_URL
  : '/data/dashboard.json';

const _ACTIONS = (typeof window.MIFTEH_ACTIONS !== 'undefined')
  ? window.MIFTEH_ACTIONS
  : {};

const _AUTH_URL = '/data/auth_config.json';

let _data = null;

// ─── Auth ─────────────────────────────────────────────────────────────────────

function _getSession() {
  try { return JSON.parse(localStorage.getItem('mifteh_session') || 'null'); }
  catch (_) { return null; }
}

function signOut() {
  localStorage.removeItem('mifteh_session');
  window.location.replace('/login.html');
}

async function initAuth() {
  const session = _getSession();

  if (!session || !session.token || !session.expires_at) {
    window.location.replace('/login.html');
    return false;
  }

  if (new Date(session.expires_at) < new Date()) {
    localStorage.removeItem('mifteh_session');
    window.location.replace('/login.html?reason=expired');
    return false;
  }

  try {
    const r = await fetch(_AUTH_URL + '?t=' + Date.now(), { cache: 'no-store' });
    if (r.ok) {
      const cfg = await r.json();
      const valid = session.token === cfg.token || session.token === cfg.prev_token;
      if (!valid) {
        localStorage.removeItem('mifteh_session');
        window.location.replace('/login.html?reason=expired');
        return false;
      }
    }
    // If auth_config fetch fails (network error), fail open — session already verified above
  } catch (_) {}

  // Show dashboard and update sidebar email
  const layout = document.getElementById('app-layout');
  if (layout) layout.style.display = '';
  const emailEl = document.getElementById('session-email');
  if (emailEl && session.email) emailEl.textContent = session.email;

  return true;
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function showTab(name, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const tab = document.getElementById('tab-' + name);
  if (tab) tab.classList.add('active');
  if (btn) btn.classList.add('active');
  const titles = {
    overview: 'AI Operations Center', loops: 'Continuous Operation Loops',
    providers: 'AI Provider Runtime', 'ai-analytics': 'AI Generation Analytics',
    outputs: 'Generated Outputs', previews: 'HTML Previews',
    repository: 'PR-Ready Changes', github: 'GitHub Draft PRs',
    analytics: 'Analytics Intelligence',
    product: 'Autonomous Product Execution',
    trust: 'Trust Scores & Autonomous Apply',
    activity: 'Operational Activity Feed', safety: 'Safety & Bounded Autonomy',
  };
  const el = document.getElementById('page-title');
  if (el) el.textContent = titles[name] || 'Dashboard';
}

// ─── Nav Search & Command Palette ────────────────────────────────────────────

function filterNav(query) {
  const q = (query || '').toLowerCase().trim();
  const nav = document.getElementById('sidebar-nav');
  if (!nav) return;
  nav.querySelectorAll('.nav-btn').forEach(btn => {
    const label = (btn.dataset.label || btn.textContent || '').toLowerCase();
    btn.style.display = (!q || label.includes(q)) ? '' : 'none';
  });
  nav.querySelectorAll('.nav-section').forEach(sec => {
    // Hide section header if all its buttons are hidden
    let next = sec.nextElementSibling;
    let anyVisible = false;
    while (next && !next.classList.contains('nav-section')) {
      if (next.style.display !== 'none') anyVisible = true;
      next = next.nextElementSibling;
    }
    sec.style.display = anyVisible ? '' : 'none';
  });
}

// ── Command palette ───────────────────────────────────────────────────────────

let _cmdSelectedIdx = -1;

function openCommandPalette() {
  const el = document.getElementById('command-palette');
  if (!el) return;
  el.style.display = 'block';
  const inp = document.getElementById('cmd-input');
  if (inp) { inp.value = ''; inp.focus(); }
  _cmdSelectedIdx = -1;
  renderCommandResults('');
}

function closeCommandPalette() {
  const el = document.getElementById('command-palette');
  if (el) el.style.display = 'none';
}

function _allNavItems() {
  const items = [];
  document.querySelectorAll('.nav-btn').forEach(btn => {
    const onclick = btn.getAttribute('onclick') || '';
    const match = onclick.match(/showTab\('([^']+)'/);
    if (match) {
      items.push({
        id: match[1],
        label: (btn.dataset.label || btn.textContent || '').trim(),
        pinned: btn.classList.contains('nav-pinned'),
        btn,
      });
    }
  });
  return items;
}

function renderCommandResults(query) {
  const q = (query || '').toLowerCase().trim();
  const items = _allNavItems();
  const filtered = q ? items.filter(i => i.label.toLowerCase().includes(q)) : items;
  const container = document.getElementById('cmd-results');
  if (!container) return;

  if (!filtered.length) {
    container.innerHTML = `<div style="padding:16px 12px;color:#64748b;text-align:center;font-size:13px">No results for "${esc(query)}"</div>`;
    return;
  }

  container.innerHTML = filtered.map((item, idx) => `
    <div class="cmd-item" data-idx="${idx}" data-tab="${esc(item.id)}"
      onclick="cmdSelectTab('${esc(item.id)}')"
      onmouseover="setCmdSelected(${idx})"
      style="padding:10px 14px;cursor:pointer;border-radius:6px;display:flex;align-items:center;gap:10px;color:#e2e8f0;font-size:13px;${idx===_cmdSelectedIdx?'background:#1e293b':''}">
      ${item.pinned ? '<span style="color:#6366f1;font-size:10px">📌</span>' : '<span style="color:#475569;font-size:12px">→</span>'}
      <span>${esc(item.label)}</span>
    </div>
  `).join('');
  _cmdSelectedIdx = -1;
}

function filterCommandPalette(value) {
  _cmdSelectedIdx = -1;
  renderCommandResults(value);
}

function setCmdSelected(idx) {
  _cmdSelectedIdx = idx;
  document.querySelectorAll('.cmd-item').forEach((el, i) => {
    el.style.background = i === idx ? '#1e293b' : '';
  });
}

function handleCmdKey(e) {
  const items = document.querySelectorAll('.cmd-item');
  if (e.key === 'Escape') { closeCommandPalette(); return; }
  if (e.key === 'ArrowDown') {
    _cmdSelectedIdx = Math.min(_cmdSelectedIdx + 1, items.length - 1);
    items.forEach((el, i) => el.style.background = i === _cmdSelectedIdx ? '#1e293b' : '');
    e.preventDefault();
  } else if (e.key === 'ArrowUp') {
    _cmdSelectedIdx = Math.max(_cmdSelectedIdx - 1, 0);
    items.forEach((el, i) => el.style.background = i === _cmdSelectedIdx ? '#1e293b' : '');
    e.preventDefault();
  } else if (e.key === 'Enter') {
    const selected = items[_cmdSelectedIdx] || items[0];
    if (selected) cmdSelectTab(selected.dataset.tab);
  }
}

function cmdSelectTab(tabId) {
  closeCommandPalette();
  const btn = document.querySelector(`.nav-btn[onclick*="'${tabId}'"]`);
  showTab(tabId, btn);
  // Scroll tab button into view
  if (btn) btn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Auto-hide empty sections ──────────────────────────────────────────────────

function autoHideEmptySections() {
  if (!window._data) return;
  // Sections that are "empty" when their primary data key is missing/zero
  const emptinessRules = [
    { section: 'previews',     check: () => !(_data.repository?.previews?.length) },
    { section: 'crosslearn',   check: () => !(_data.cross_project?.projects) },
    { section: 'sandbox',      check: () => !(_data.sandbox?.active_sandboxes) },
    { section: 'research',     check: () => !(_data.research?.projects_researched) },
    { section: 'cognition',    check: () => !(_data.cognition?.health_score) },
    { section: 'civilization', check: () => !(_data.kernel?.company_mode) },
    { section: 'agents',       check: () => !(_data.agent_bus?.active_agents?.length) },
    { section: 'economy',      check: () => !(_data.task_economy?.portfolio) },
  ];

  emptinessRules.forEach(rule => {
    const btn = document.querySelector(`.nav-btn[onclick*="'${rule.section}'"]`);
    if (!btn) return;
    const isEmpty = rule.check();
    btn.style.opacity = isEmpty ? '0.35' : '';
    btn.title = isEmpty ? 'No data yet — will populate when workflows run' : '';
  });
}

// ── Focus mode banner ─────────────────────────────────────────────────────────

function renderFocusBanner(d) {
  const fm = d.focus_mode || {};
  if (!fm.active && !fm.mode) return;
  const badge = document.getElementById('focus-mode-badge');
  const banner = document.getElementById('focus-banner');
  const bannerText = document.getElementById('focus-banner-text');
  const bannerExpires = document.getElementById('focus-banner-expires');
  if (badge) badge.style.display = '';
  if (banner) banner.style.display = '';
  if (bannerText) bannerText.textContent = fm.label || 'Focus Mode active';
  if (bannerExpires && fm.expires_at) {
    bannerExpires.textContent = `Expires ${fm.expires_at.slice(0, 10)}`;
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function relTime(iso) {
  if (!iso) return '–';
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 5) return 'just now';
  if (diff < 60) return diff + 's ago';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

function formatNext(iso) {
  if (!iso) return '–';
  const diff = Math.floor((new Date(iso) - Date.now()) / 1000);
  if (diff < 0) return 'now';
  if (diff < 60) return 'in ' + diff + 's';
  if (diff < 3600) return 'in ' + Math.floor(diff / 60) + 'm';
  return 'in ' + Math.floor(diff / 3600) + 'h ' + Math.floor((diff % 3600) / 60) + 'm';
}

function fmtInterval(mins) {
  if (!mins) return '–';
  if (mins < 60) return mins + 'm';
  if (mins < 1440) return (mins / 60) + 'h';
  return (mins / 1440) + 'd';
}

function card(label, value, cls, sub) {
  return `<div class="card ${cls || ''}">
    <div class="card-label">${esc(label)}</div>
    <div class="card-value">${esc(String(value))}</div>
    ${sub ? `<div class="card-sub">${esc(sub)}</div>` : ''}
  </div>`;
}

function statusDot(status) {
  const map = { completed: 'dot-green', running: 'dot-blue', pending: 'dot-yellow', error: 'dot-red', failed: 'dot-red', queued: 'dot-yellow' };
  return `<span class="status-dot ${map[status] || 'dot-dim'}"></span>`;
}

function aiBadge(ai) {
  return ai
    ? '<span class="activity-badge badge-green">🤖 AI</span>'
    : '<span class="activity-badge badge-dim">📝 template</span>';
}

function projectTag(project) {
  if (project === 'yallaplays') return '<span class="project-tag yp-tag">YP</span>';
  if (project === 'mifteh') return '<span class="project-tag" style="background:#2d1a4a;color:#a855f7;">MI</span>';
  return '<span class="project-tag fi-tag">FI</span>';
}

function provBadge(configured, available) {
  if (!configured) return '<span class="panel-badge badge-dim">not configured</span>';
  if (available) return '<span class="panel-badge badge-green">live</span>';
  return '<span class="panel-badge badge-yellow">rate limited</span>';
}

function set(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function statRow(label, value, color) {
  return `<div class="provider-stat"><span>${esc(label)}</span><span${color ? ` style="color:${color};"` : ''}>${esc(String(value))}</span></div>`;
}

// ─── Overview ────────────────────────────────────────────────────────────────

function renderOverview(d) {
  const sched = d.scheduler || {};
  const outs = d.outputs || {};
  const prov = d.providers || {};
  const ai = d.ai_analytics || {};
  const ghs = (d.github_prs || []).length;

  set('overview-cards',
    card('Total Outputs', outs.total || 0, 'green', 'all projects') +
    card('AI Generated', outs.ai_generated || 0, 'blue', `${ai.ai_generated_pct || 0}% AI rate`) +
    card('Pending Review', outs.pending_review || 0, 'yellow', 'awaiting apply') +
    card('GitHub PRs', ghs, 'purple', 'draft PRs created') +
    card('Active Loops', sched.active_loops || 0, 'cyan', `of ${sched.total_loops || 14}`) +
    card('AI Cost (7d)', `$${(ai.total_cost_usd || 0).toFixed(4)}`, 'orange', `${ai.total_tokens || 0} tokens`)
  );

  set('scheduler-badge', '<span class="panel-badge badge-green">GitHub Actions</span>');
  set('scheduler-summary',
    statRow('Runtime', 'GitHub Actions', 'var(--cyan)') +
    statRow('Architecture', 'GitHub-native', 'var(--green)') +
    statRow('Active Loops', `${sched.active_loops || 0} / ${sched.total_loops || 14}`) +
    statRow('Total Runs', sched.total_runs || 0) +
    statRow('Successful', sched.total_success || 0, 'var(--green)') +
    statRow('Generation Mode', prov.ai_mode || 'ai', 'var(--cyan)')
  );

  const oai = prov.openai || {};
  const gem = prov.gemini || {};
  const aiMode = prov.ai_mode || 'ai';
  set('provider-badge', aiMode === 'ai' ? '<span class="panel-badge badge-green">AI active</span>' : '<span class="panel-badge badge-yellow">template mode</span>');
  set('provider-summary',
    `<div class="provider-stat"><span>OpenAI</span>${provBadge(oai.configured, oai.available)}</div>` +
    `<div class="provider-stat"><span>Gemini</span>${provBadge(gem.configured, gem.available)}</div>` +
    statRow('GitHub', prov.github_active ? 'active' : '–', prov.github_active ? 'var(--green)' : 'var(--dim)') +
    statRow('AI Cost (7d)', `$${(ai.total_cost_usd || 0).toFixed(4)}`) +
    statRow('AI Success Rate', `${ai.success_rate_pct || 0}%`, ai.success_rate_pct > 50 ? 'var(--green)' : 'var(--yellow)')
  );

  const activity = d.activity || [];
  set('recent-outputs-mini', activity.slice(0, 6).map(o => `
    <div class="output-row">${projectTag(o.project)}<span class="output-type-tag">${esc(o.type)}</span>
    <span class="output-title">${esc(o.title)}</span>${aiBadge(o.ai_generated)}</div>
  `).join('') || '<div class="empty">Waiting for first AI loop run…</div>');

  const prs = d.github_prs || [];
  set('github-mini', prs.length ? prs.slice(0, 5).map(p => `
    <div class="pr-row">
      <div class="pr-body">
        <div class="pr-branch">${esc(p.branch)}</div>
        <div class="pr-meta"><a href="${esc(p.pr_url)}" target="_blank" style="color:var(--blue);">PR #${p.pr_number}</a> · ${esc(p.repo)} · ${relTime(p.created_at)}</div>
      </div>${projectTag(p.repo && p.repo.toLowerCase().includes('yalla') ? 'yallaplays' : 'fionera')}
    </div>
  `).join('') : '<div class="empty">No GitHub PRs yet. AI PR Generator runs daily at 08:00 UTC.</div>');

  renderActivityList('activity-mini', activity.slice(0, 8));
  set('activity-badge-overview', `<span class="panel-badge badge-dim">${activity.length} events</span>`);
}

// ─── Loops ───────────────────────────────────────────────────────────────────

function renderLoops(d) {
  const loops = (d.scheduler || {}).loops || [];
  const workflowUrl = (loop) => {
    if (loop.project === 'yallaplays' || loop.project === 'mifteh') return _ACTIONS.seo || '#';
    if (loop.project === 'fionera') return _ACTIONS.finance || '#';
    return _ACTIONS.dashboard || '#';
  };
  function row(l) {
    const next = l.next_run_scheduled || l.next_run;
    return `<tr>
      <td>${statusDot(l.last_status || 'pending')}<span style="color:var(--muted);font-size:11px;">${esc(l.last_status || 'pending')}</span></td>
      <td style="font-weight:600;">${esc(l.label)}</td>
      <td><span class="countdown">${fmtInterval(l.interval_minutes)}</span></td>
      <td style="color:var(--dim);">${relTime(l.last_run)}</td>
      <td><span class="countdown">${formatNext(next)}</span></td>
      <td style="color:var(--muted);">${l.run_count || 0}</td>
      <td style="color:var(--green);">${l.success_count || 0}</td>
      <td><a href="${esc(workflowUrl(l))}" target="_blank" class="trigger-btn" style="text-decoration:none;">▶ Run</a></td>
    </tr>`;
  }
  const yp = loops.filter(l => l.project === 'yallaplays');
  const fi = loops.filter(l => l.project === 'fionera');
  const mi = loops.filter(l => l.project === 'mifteh');
  set('yp-loops-body', yp.map(row).join('') || '<tr><td colspan="8" class="empty">No loops</td></tr>');
  set('fi-loops-body', fi.map(row).join('') || '<tr><td colspan="8" class="empty">No loops</td></tr>');
  set('mi-loops-body', mi.map(row).join('') || '<tr><td colspan="8" class="empty">No loops</td></tr>');
}

// ─── Providers ───────────────────────────────────────────────────────────────

function renderProviders(d) {
  const prov = d.providers || {};
  const cool = (d.scheduler || {}).provider_cooldowns || {};
  const names = ['openai', 'gemini'];
  set('providers-cards', names.map(n => {
    const p = cool[n] || {};
    const cfg = prov[n] || {};
    const avail = cfg.available !== undefined ? cfg.available : p.available;
    return `<div class="provider-card">
      <div class="provider-name">${avail ? '🟢' : '🟡'} ${n.toUpperCase()}</div>
      ${statRow('Configured', (prov[n] || {}).configured ? 'yes' : 'no')}
      ${statRow('Available', avail ? 'yes' : 'no', avail ? 'var(--green)' : 'var(--yellow)')}
      ${statRow('429s (consecutive)', p.consecutive_429s || 0)}
      ${statRow('429s (total)', p.total_429s || 0)}
    </div>`;
  }).join('') + `<div class="provider-card">
    <div class="provider-name">⚙️ Runtime</div>
    ${statRow('Architecture', 'GitHub-native', 'var(--cyan)')}
    ${statRow('Scheduler', 'GitHub Actions', 'var(--green)')}
    ${statRow('Storage', 'Repository JSON', 'var(--muted)')}
    ${statRow('GitHub', prov.github_active ? 'active' : '–', prov.github_active ? 'var(--green)' : 'var(--dim)')}
  </div>`);

  set('providers-detail', names.map(n => {
    const p = cool[n] || {};
    return `<div style="margin-bottom:14px;">
      <div style="font-weight:700;font-size:13px;margin-bottom:8px;">${n.toUpperCase()}</div>
      ${statRow('Last Success', relTime(p.last_success))}
      ${statRow('Last Rate Limit', p.last_429 ? relTime(p.last_429) : '–')}
      ${statRow('Cooldown Until', p.cooldown_until ? new Date(p.cooldown_until).toLocaleTimeString() : '–')}
    </div>`;
  }).join('<hr style="border-color:var(--border);margin:8px 0;">'));
}

// ─── AI Analytics ────────────────────────────────────────────────────────────

function renderAIAnalytics(d) {
  const ai = d.ai_analytics || {};
  set('ai-analytics-cards',
    card('Total AI Calls', ai.total_calls || 0, 'blue') +
    card('Successful', ai.successful_calls || 0, 'green', `${ai.success_rate_pct || 0}% success`) +
    card('Rate Limited', ai.rate_limited_calls || 0, 'yellow') +
    card('AI Gen %', `${ai.ai_generated_pct || 0}%`, 'purple') +
    card('Total Tokens', (ai.total_tokens || 0).toLocaleString(), 'cyan') +
    card('Total Cost', `$${(ai.total_cost_usd || 0).toFixed(6)}`, 'orange')
  );

  const byProv = ai.by_provider || {};
  set('ai-by-provider', Object.keys(byProv).length ? Object.entries(byProv).map(([name, stats]) => `
    <div style="margin-bottom:12px;">
      <div style="font-weight:700;font-size:12px;margin-bottom:6px;">${esc(name)}</div>
      ${statRow('Requests', stats.requests || 0)}
      ${statRow('Success Rate', `${stats.success_rate || 100}%`, 'var(--green)')}
      ${statRow('Total Tokens', (stats.tokens || 0).toLocaleString())}
      ${statRow('Total Cost', `$${(stats.cost_usd || 0).toFixed(6)}`)}
    </div>
    <hr style="border-color:var(--border);margin:8px 0;">
  `).join('') : '<div class="empty">No AI calls yet — workflows start generating on next cron run</div>');

  const byProj = ai.by_project || {};
  set('ai-by-project', Object.keys(byProj).length ? Object.entries(byProj).map(([proj, count]) => `
    <div class="output-row">${projectTag(proj)}<span class="output-title">${esc(proj)}</span><span style="color:var(--cyan);">${count} calls</span></div>
  `).join('') : '<div class="empty">No data</div>');

  const byOp = ai.by_operation_type || {};
  set('ai-by-optype', Object.keys(byOp).length ? Object.entries(byOp).sort((a, b) => b[1] - a[1]).map(([op, count]) => `
    <div class="output-row"><span class="output-type-tag">${esc(op)}</span><span class="output-title"></span><span style="color:var(--muted);">${count} calls</span></div>
  `).join('') : '<div class="empty">No data</div>');

  const byDay = ai.by_day || {};
  const days = Object.entries(byDay).sort((a, b) => a[0].localeCompare(b[0]));
  set('ai-daily-trend', days.length ? days.map(([day, stats]) => `
    <div class="output-row">
      <span style="font-size:11px;color:var(--dim);font-family:monospace;width:90px;flex-shrink:0;">${esc(day)}</span>
      <span class="output-title"></span>
      <span style="color:var(--green);">${stats.success || 0}✓</span>
      <span style="color:var(--muted);margin-left:8px;">${stats.requests || 0} calls</span>
      <span style="color:var(--orange);margin-left:8px;">$${(stats.cost_usd || 0).toFixed(4)}</span>
    </div>
  `).join('') : '<div class="empty">No daily data yet</div>');
}

// ─── Outputs ─────────────────────────────────────────────────────────────────

function renderOutputs(d) {
  const outs = d.outputs || {};
  set('outputs-cards',
    card('Total', outs.total || 0, 'green') +
    card('YallaPlays', outs.yallaplays || 0, 'cyan') +
    card('Fionera', outs.fionera || 0, 'blue') +
    card('Mifteh', outs.mifteh || 0, 'purple') +
    card('AI Generated', outs.ai_generated || 0, 'green') +
    card('Pending Review', outs.pending_review || 0, 'yellow')
  );
  const activity = d.activity || [];
  const outputRows = (list) => list.length ? list.map(o => `
    <div class="output-row"><span class="output-type-tag">${esc(o.type)}</span>
    <span class="output-title">${esc(o.title)}</span>${aiBadge(o.ai_generated)}
    <span style="font-size:10px;color:var(--dim);">${relTime(o.time)}</span></div>
  `).join('') : '<div class="empty">No outputs yet</div>';
  set('yp-outputs-list', outputRows(activity.filter(o => o.project === 'yallaplays')));
  set('fi-outputs-list', outputRows(activity.filter(o => o.project === 'fionera')));
}

// ─── Previews ────────────────────────────────────────────────────────────────

function _qaGradeColor(grade) {
  return { A: '#22c55e', B: '#84cc16', C: '#eab308', D: '#f97316', F: '#ef4444' }[grade] || '#64748b';
}

function _qaBar(score, max) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 70 ? '#22c55e' : pct >= 50 ? '#eab308' : '#ef4444';
  return `<div style="display:flex;align-items:center;gap:6px;">
    <div style="flex:1;height:4px;background:#1e293b;border-radius:2px;">
      <div style="width:${pct}%;height:4px;background:${color};border-radius:2px;"></div>
    </div>
    <span style="font-size:11px;color:var(--dim);min-width:32px;">${score}/${max}</span>
  </div>`;
}

function renderPreviews(d) {
  const qa = d.visual_qa || {};
  const reports = qa.reports || [];

  // Overview cards
  const cards = [
    { label: 'QA Total', value: qa.total || 0, color: 'var(--cyan)' },
    { label: 'Passing', value: qa.passing || 0, color: 'var(--green)' },
    { label: 'Blocked', value: qa.blocking || 0, color: (qa.blocking || 0) > 0 ? 'var(--red)' : 'var(--dim)' },
    { label: 'Avg Score', value: (qa.avg_score || 0) + '/100', color: 'var(--yellow)' },
  ];
  set('qa-overview-cards', cards.map(c => `
    <div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>
  `).join(''));

  set('previews-badge', `<span class="panel-badge badge-dim">${reports.length} files</span>`);

  // QA score cards
  if (reports.length) {
    set('qa-score-cards', reports.map(r => {
      const cats = r.categories || {};
      const passes = r.passes;
      const gc = _qaGradeColor(r.grade);
      const preview_path = `../previews/${r.project}/${(r.label||'').replace(/^[^_]+_/, '')}.html`;
      return `<div class="panel full" style="margin-bottom:12px;border-left:3px solid ${gc};">
        <div class="panel-header" style="flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:10px;flex:1;">
            <span style="font-size:22px;font-weight:800;color:${gc};">${r.grade}</span>
            <div>
              <div class="panel-title" style="margin:0;">${esc(r.label)}</div>
              <div style="font-size:11px;color:var(--dim);">${esc(r.project)} · ${r.score}/100 · ${relTime(r.validated_at)}</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:center;">
            <span class="panel-badge ${passes ? 'badge-green' : 'badge-yellow'}">${passes ? '✓ PASS' : '✗ BLOCKED'}</span>
            ${r.pr_url ? `<a href="${esc(r.pr_url)}" target="_blank" style="font-size:11px;color:var(--blue);">PR →</a>` : ''}
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:12px 0;">
          ${Object.entries(cats).map(([cat, v]) => `
            <div>
              <div style="font-size:11px;color:var(--dim);margin-bottom:4px;">${cat.charAt(0).toUpperCase()+cat.slice(1)}</div>
              ${_qaBar(v.score, v.max)}
            </div>
          `).join('')}
        </div>
        ${r.top_issues && r.top_issues.length ? `
          <div style="font-size:11px;color:var(--dim);margin-top:6px;">
            ${r.top_issues.map(i => `<div style="padding:2px 0;">• ${esc(i)}</div>`).join('')}
          </div>` : ''}
      </div>`;
    }).join(''));
  } else {
    set('qa-score-cards', '<div class="empty">No QA reports yet — run Visual Preview workflow</div>');
  }

  // Preview gallery
  set('previews-list', reports.length ? reports.map(r => {
    const proj = r.project || '';
    const feat = (r.label || '').replace(/^[^_]+_/, '');
    const preview_href = `/previews/${proj}/${feat}.html`;
    return `<div class="output-row">
      <span class="output-type-tag" style="background:${_qaGradeColor(r.grade)};color:#000;font-weight:700;">${r.grade}</span>
      <span class="output-title">${esc(r.label)}</span>
      <span style="font-size:11px;color:var(--dim);margin-left:4px;">${r.score}/100</span>
      <a href="${esc(r.pr_url||'#')}" target="_blank" style="font-size:11px;color:var(--blue);margin-left:auto;">PR →</a>
    </div>`;
  }).join('') : '<div class="empty">No previews yet — run ai-visual-preview workflow</div>');
}

// ─── System Health ────────────────────────────────────────────────────────────

function renderHealth(d) {
  const si = d.self_improvement || {};
  const raw = si.raw_metrics || {};
  const outputs = raw.outputs || {};
  const workflows = raw.workflows || {};
  const qa = raw.visual_qa || {};
  const automerge = raw.automerge || {};

  // Overview cards
  const health_score = si.overall_health_score || 0;
  const eff_score = si.efficiency_score || 0;
  const qual_score = si.quality_score || 0;
  const vel_score = si.velocity_score || 0;

  const healthColor = health_score >= 80 ? 'var(--green)' : health_score >= 60 ? 'var(--yellow)' : 'var(--red)';

  set('health-overview-cards', [
    { label: 'System Health', value: health_score + '/100', color: healthColor },
    { label: 'Efficiency', value: eff_score + '/100', color: 'var(--cyan)' },
    { label: 'Quality', value: qual_score + '/100', color: 'var(--blue)' },
    { label: 'Velocity', value: vel_score + '/100', color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  // Token & cost detail
  const avgTok = outputs.avg_tokens_per_feature || 0;
  const avgCost = (outputs.avg_cost_per_feature_usd || 0).toFixed(5);
  const tokEff = outputs.token_efficiency || 0;
  const totalCost = (outputs.total_cost_usd || 0).toFixed(4);
  const vel7d = outputs.features_last_7d || 0;

  set('health-token-badge', `<span class="panel-badge badge-dim">${outputs.total || 0} total</span>`);
  set('health-token-detail', `
    <div class="output-row"><span class="output-type-tag" style="background:#7c3aed">TOKEN</span>
      <div><div class="output-title">Avg tokens/feature</div><div class="output-meta">${avgTok.toLocaleString()}</div></div></div>
    <div class="output-row"><span class="output-type-tag" style="background:#0284c7">COST</span>
      <div><div class="output-title">Avg cost/feature</div><div class="output-meta">$${avgCost}</div></div></div>
    <div class="output-row"><span class="output-type-tag" style="background:#0f766e">EFF</span>
      <div><div class="output-title">Token efficiency</div><div class="output-meta">${tokEff} features/1K tokens</div></div></div>
    <div class="output-row"><span class="output-type-tag" style="background:#16a34a">COST</span>
      <div><div class="output-title">Total AI cost</div><div class="output-meta">$${totalCost}</div></div></div>
    <div class="output-row"><span class="output-type-tag" style="background:#d97706">VEL</span>
      <div><div class="output-title">Features (7d)</div><div class="output-meta">${vel7d}</div></div></div>
  `);

  // Workflow detail
  const wfCount = workflows.total || 0;
  const mergeRate = automerge.merge_rate_pct || 0;
  const avgMergeSc = automerge.avg_merge_score || 0;
  const qaPass = (d.visual_qa || {}).pass_rate_pct || 0;

  set('health-workflow-badge', `<span class="panel-badge badge-dim">${wfCount} workflows</span>`);
  set('health-workflow-detail', `
    <div class="output-row"><span class="output-type-tag" style="background:#1d4ed8">WF</span>
      <div><div class="output-title">Active workflows</div><div class="output-meta">${wfCount}</div></div></div>
    <div class="output-row"><span class="output-type-tag" style="background:#15803d">MERGE</span>
      <div><div class="output-title">Auto-merge rate</div><div class="output-meta">${mergeRate}% (avg score ${avgMergeSc}/100)</div></div></div>
    <div class="output-row"><span class="output-type-tag" style="background:#7c3aed">QA</span>
      <div><div class="output-title">Visual QA pass rate</div><div class="output-meta">${qaPass}%</div></div></div>
  ` + (si.health_summary ? `<div style="margin-top:12px;padding:10px;background:#0f1929;border-radius:6px;font-size:12px;color:var(--dim);">${esc(si.health_summary)}</div>` : ''));

  // Self-improvement recommendations
  const improvements = si.top_improvements || [];
  set('health-improve-badge', `<span class="panel-badge badge-cyan">${improvements.length}</span>`);
  if (improvements.length) {
    const catColor = { token_efficiency: '#7c3aed', prompt_quality: '#0284c7', workflow_health: '#16a34a', qa_quality: '#eab308', cost_reduction: '#dc2626', velocity: '#f97316' };
    set('health-improvements-list', improvements.map((imp, i) => {
      const pColor = { high: 'var(--red)', medium: 'var(--yellow)', low: 'var(--dim)' }[imp.priority] || 'var(--dim)';
      const cc = catColor[imp.category] || '#64748b';
      return `<div style="padding:14px;border:1px solid #1e293b;border-radius:8px;margin-bottom:10px;border-left:3px solid ${cc};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;">
          <div style="font-weight:600;font-size:13px;">${i+1}. ${esc(imp.title)}</div>
          <div style="display:flex;gap:6px;flex-shrink:0;">
            <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:#0f172a;border:1px solid ${pColor};color:${pColor};">${imp.priority}</span>
            <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${cc}22;color:${cc};">${imp.category}</span>
          </div>
        </div>
        <div style="font-size:12px;color:var(--dim);margin-bottom:6px;">${esc(imp.description)}</div>
        <div style="font-size:11px;color:var(--blue);">Impact: ${esc(imp.estimated_impact)}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:2px;">Effort: ${esc(imp.effort)}</div>
      </div>`;
    }).join(''));
  } else {
    const msg = si.overall_health_score
      ? `<div style="padding:10px;font-size:12px;color:var(--green);">${esc(si.health_summary || 'System is healthy')}</div>`
      : '<div class="empty">Run the Self-Improvement workflow to get AI recommendations</div>';
    set('health-improvements-list', msg);
  }
}

// ─── Repository ──────────────────────────────────────────────────────────────

function renderRepository(d) {
  const prOuts = (d.repository || {}).pr_outputs || [];
  set('pr-badge', `<span class="panel-badge badge-dim">${prOuts.length} outputs</span>`);
  set('pr-outputs-list', prOuts.length ? prOuts.map(p => `
    <div class="pr-row">${projectTag(p.project)}
      <div class="pr-body">
        <div class="pr-branch">${esc(p.suggested_branch)}</div>
        <div class="pr-meta">${esc(p.output_type)} · ${p.total_files || 0} file(s) · ${relTime(p.generated_at)}</div>
      </div>
      <a href="${esc(_ACTIONS.prs || '#')}" target="_blank" class="trigger-btn" style="text-decoration:none;flex-shrink:0;">⑂ PR</a>
    </div>
  `).join('') : '<div class="empty">No PR-ready outputs yet — runs after first AI loop</div>');
}

// ─── GitHub ──────────────────────────────────────────────────────────────────

function renderGitHub(d) {
  const prs = d.github_prs || [];
  set('github-badge', `<span class="panel-badge badge-dim">${prs.length} PRs</span>`);
  set('github-prs-list', prs.length ? prs.map(p => `
    <div class="pr-row">
      <div style="font-size:18px;flex-shrink:0;">⑂</div>
      <div class="pr-body">
        <div><a href="${esc(p.pr_url)}" target="_blank" style="color:var(--blue);font-weight:600;font-size:13px;">PR #${p.pr_number} — ${esc(p.pr_title)}</a></div>
        <div class="pr-branch" style="margin-top:4px;">${esc(p.branch)}</div>
        <div class="pr-meta">${esc(p.repo)} · ${(p.files_committed || []).length} files · ${relTime(p.created_at)} · <span style="color:var(--yellow);">draft</span></div>
      </div>
    </div>
  `).join('') : '<div class="empty">No GitHub PRs yet. AI PR Generator runs daily at 08:00 UTC.<br>Manually trigger via GitHub Actions → MIFTEH AI PR Generator.</div>');
}

// ─── Activity ────────────────────────────────────────────────────────────────

function renderActivityList(id, items) {
  if (!items || !items.length) { set(id, '<div class="empty">No activity yet — waiting for first workflow run</div>'); return; }
  const icons = { seo_page: '🔍', category_page: '📂', metadata_patch: '🏷', mobile_optimization: '📱', internal_linking: '🔗', game_recommendation: '🎮', market_insight: '📈', finance_widget: '💹', watchlist_improvement: '👁', analytics_report: '📊', content_optimization: '✍️', analytics_dashboard: '📊', ux_proposal: '✨' };
  const colors = { yallaplays: '#16a34a', fionera: '#2563eb', mifteh: '#7c3aed' };
  set(id, items.map(o => `
    <div class="activity-item">
      <div class="activity-icon" style="background:${colors[o.project] || '#374151'}20;color:${colors[o.project] || '#9ca3af'};">${icons[o.type] || '◻'}</div>
      <div class="activity-body">
        <div class="activity-title">${esc(o.title)}</div>
        <div class="activity-meta">${esc(o.project)} · ${esc(o.type)} · ${relTime(o.time)}</div>
      </div>${aiBadge(o.ai_generated)}
    </div>
  `).join(''));
}

function renderActivity(d) { renderActivityList('activity-full', d.activity || []); }

// ─── Safety ──────────────────────────────────────────────────────────────────

function renderSafety(d) {
  const safety = d.safety || {};
  const outs = d.outputs || {};
  const constraints = [
    ['🚫 Auto-merge', !safety.auto_merge],
    ['🚫 Auto-deploy', !safety.auto_deploy],
    ['✅ Preview-first', safety.preview_first],
    ['✅ Rollback enabled', safety.rollback_enabled],
    ['✅ Validation required', safety.validation_required],
    ['✅ Audit tracking', safety.audit_tracking],
  ];
  set('safety-constraints', `<div class="safety-grid">${constraints.map(([l, ok]) =>
    `<div class="safety-item"><span class="safety-icon">${ok ? '🟢' : '🔴'}</span><span style="color:${ok ? 'var(--green)' : 'var(--red)'};">${esc(l)}</span></div>`
  ).join('')}</div>`);
  set('safety-limits',
    statRow('Runtime', 'GitHub Actions') +
    statRow('Storage', 'Repository JSON') +
    statRow('AI Provider', 'OpenAI gpt-4o-mini') +
    statRow('Bounded Autonomy', 'active', 'var(--green)') +
    statRow('Auth Required', 'no (read-only dashboard)', 'var(--dim)') +
    statRow('PR Type', 'always draft', 'var(--green)')
  );
  set('safety-audit',
    statRow('Total Outputs Generated', outs.total || 0) +
    statRow('AI-Generated', outs.ai_generated || 0) +
    statRow('Template Outputs', outs.template_generated || 0) +
    statRow('Pending Human Review', outs.pending_review || 0, 'var(--yellow)') +
    statRow('PR-Ready Changes', (d.repository || {}).pr_ready || 0, 'var(--purple)') +
    statRow('GitHub PRs Created', (d.github_prs || []).length, 'var(--blue)') +
    `<div style="margin-top:12px;padding:10px;background:var(--surface2);border-radius:var(--radius-sm);font-size:11px;color:var(--muted);">
      ⛨ GitHub-native autonomous AI OS. No auto-merge, no auto-deploy, no bypass of review.
      All outputs require human approval. PRs always created as drafts.
      Architecture: GitHub Actions → outputs/ → dashboard.json → miftehos.com
    </div>`
  );
}

// ─── Analytics Intelligence ──────────────────────────────────────────────────

function scoreBar(score, label) {
  const pct = Math.max(0, Math.min(100, score || 0));
  const color = pct >= 75 ? 'var(--green)' : pct >= 55 ? 'var(--yellow)' : 'var(--red)';
  return `<div style="margin-bottom:8px;">
    <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
      <span style="font-size:11px;color:var(--muted);">${esc(label)}</span>
      <span style="font-size:11px;font-weight:700;color:${color};">${pct}</span>
    </div>
    <div style="height:4px;background:var(--surface2);border-radius:2px;">
      <div style="width:${pct}%;height:100%;background:${color};border-radius:2px;transition:width .4s;"></div>
    </div>
  </div>`;
}

function trendBadge(trend) {
  if (!trend) return '';
  const map = { up: ['↑', 'var(--green)'], down: ['↓', 'var(--red)'], stable: ['→', 'var(--dim)'] };
  const [icon, color] = map[trend] || ['–', 'var(--dim)'];
  return `<span style="color:${color};font-weight:700;">${icon}</span>`;
}

function priorityBadge(priority) {
  const map = {
    critical: ['CRITICAL', 'var(--red)'],
    high: ['HIGH', 'var(--orange)'],
    medium: ['MED', 'var(--yellow)'],
    low: ['LOW', 'var(--dim)'],
  };
  const [label, color] = map[(priority||'').toLowerCase()] || [priority||'', 'var(--dim)'];
  return `<span style="font-size:10px;font-weight:700;color:${color};border:1px solid ${color};padding:1px 5px;border-radius:3px;">${label}</span>`;
}

function fmtNum(n) {
  if (!n) return '0';
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return String(n);
}

function projectAnalyticsBlock(projData) {
  if (!projData) return '<div class="empty">No analytics data yet</div>';
  const ov = projData.overview || {};
  const sc = projData.scores || {};
  const eng = projData.engagement || {};
  const conv = projData.conversions || {};
  const topPages = projData.top_pages || [];
  const lowPages = projData.low_pages || [];
  const queries = projData.search_queries || [];

  return `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:14px;">
      <div>
        ${statRow('Monthly Visits', fmtNum(ov.monthly_visits), 'var(--cyan)')}
        ${statRow('Bounce Rate', `${(ov.bounce_rate_pct||0).toFixed(1)}%`, ov.bounce_rate_pct > 55 ? 'var(--red)' : 'var(--green)')}
        ${statRow('Avg Session', `${Math.round((ov.avg_session_seconds||0)/60)}m ${(ov.avg_session_seconds||0)%60}s`)}
        ${statRow('Mobile', `${(ov.mobile_pct||0).toFixed(0)}%`, 'var(--muted)')}
        ${statRow('Organic Search', `${(ov.organic_search_pct||0).toFixed(0)}%`, 'var(--green)')}
        ${statRow('Weekly Change', `${ov.weekly_change_pct>=0?'+':''}${(ov.weekly_change_pct||0).toFixed(1)}%`, ov.weekly_change_pct>=0?'var(--green)':'var(--red)')}
      </div>
      <div>
        ${scoreBar(sc.performance_score, 'Performance')}
        ${scoreBar(sc.engagement_score, 'Engagement')}
        ${scoreBar(sc.seo_opportunity_score, 'SEO Opportunity')}
        ${scoreBar(sc.conversion_score, 'Conversion')}
      </div>
    </div>
    ${topPages.length ? `
    <div style="font-size:11px;font-weight:700;color:var(--muted);margin-bottom:6px;">TOP PAGES</div>
    ${topPages.slice(0,4).map(p => `
      <div class="output-row" style="font-size:11px;padding:4px 0;">
        ${trendBadge(p.trend)}
        <code style="color:var(--dim);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(p.path)}</code>
        <span style="color:var(--cyan);flex-shrink:0;">${fmtNum(p.monthly_visits)}</span>
        <span style="color:var(--muted);flex-shrink:0;margin-left:8px;">${(p.bounce_pct||0).toFixed(0)}% bounce</span>
      </div>
    `).join('')}` : ''}
    ${queries.length ? `
    <div style="font-size:11px;font-weight:700;color:var(--muted);margin:10px 0 6px;">TOP QUERIES</div>
    ${queries.slice(0,4).map(q => `
      <div class="output-row" style="font-size:11px;padding:3px 0;">
        <span class="output-type-tag" style="font-size:10px;">${esc(q.opportunity||'?')}</span>
        <span style="flex:1;">${esc(q.query)}</span>
        <span style="color:var(--green);flex-shrink:0;">${fmtNum(q.clicks)} clicks</span>
        <span style="color:var(--dim);flex-shrink:0;margin-left:8px;">pos ${(q.avg_position||0).toFixed(1)}</span>
      </div>
    `).join('')}` : ''}
    ${projData.top_opportunity ? `
    <div style="margin-top:10px;padding:8px;background:var(--surface2);border-radius:var(--radius-sm);border-left:2px solid var(--cyan);">
      <div style="font-size:10px;font-weight:700;color:var(--cyan);margin-bottom:3px;">TOP OPPORTUNITY</div>
      <div style="font-size:12px;color:var(--text);">${esc(projData.top_opportunity)}</div>
    </div>` : ''}
  `;
}

function renderAnalytics(d) {
  const ai = d.analytics_intelligence || {};
  const cp = ai.cross_project || {};
  const projects = ai.projects || {};
  const recs = ai.recommendations || [];
  const alerts = ai.alert_thresholds || [];
  const queue = ai.autonomous_decisions || [];

  const totalVisits = cp.total_monthly_visits || 0;
  const health = cp.overall_portfolio_health || 0;

  set('analytics-overview-cards',
    card('Portfolio Visits', fmtNum(totalVisits), 'cyan', 'monthly across all projects') +
    card('Health Score', health || '–', health >= 70 ? 'green' : 'yellow', 'portfolio avg') +
    card('AI Recommendations', recs.length, 'blue', 'prioritized actions') +
    card('Decision Queue', queue.length, 'purple', 'autonomous tasks') +
    card('Active Alerts', alerts.length, alerts.length > 3 ? 'red' : 'yellow', 'needs attention') +
    card('Est. Traffic Gain', `+${fmtNum((ai.estimated_impact||{}).monthly_visits_gain||0)}`, 'green', 'if queue executed')
  );

  // Portfolio summary
  const trendIcon = { up: '↑', down: '↓', stable: '→' }[cp.month_over_month_trend] || '→';
  const trendColor = cp.month_over_month_trend === 'up' ? 'var(--green)' : cp.month_over_month_trend === 'down' ? 'var(--red)' : 'var(--dim)';
  set('analytics-health-badge', `<span class="panel-badge ${health>=70?'badge-green':'badge-yellow'}">${health}/100</span>`);
  set('analytics-portfolio-summary',
    statRow('Total Monthly Visits', fmtNum(totalVisits), 'var(--cyan)') +
    statRow('Trend', `${trendIcon} ${esc(cp.month_over_month_trend||'stable')}`, trendColor) +
    statRow('Strongest Project', esc(cp.strongest_project||'–'), 'var(--green)') +
    statRow('Highest SEO Opportunity', esc(cp.highest_seo_opportunity||'–'), 'var(--cyan)') +
    statRow('Most Critical Issues', esc(cp.most_critical_issues||'–'), 'var(--yellow)') +
    (cp.insight ? `<div style="margin-top:10px;padding:8px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;color:var(--muted);">💡 ${esc(cp.insight)}</div>` : '')
  );

  // Alerts
  set('analytics-alerts-badge', `<span class="panel-badge ${alerts.length?'badge-yellow':'badge-dim'}">${alerts.length}</span>`);
  set('analytics-alerts-list', alerts.length ? alerts.map(a => {
    const sevColor = { critical: 'var(--red)', warning: 'var(--yellow)', info: 'var(--cyan)' }[a.severity] || 'var(--dim)';
    return `<div style="padding:8px;border-left:2px solid ${sevColor};background:var(--surface2);margin-bottom:6px;border-radius:0 4px 4px 0;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
        <span style="font-size:11px;font-weight:700;color:${sevColor};">${esc((a.severity||'').toUpperCase())}</span>
        <span style="font-size:10px;color:var(--dim);">${projectTag(a.project||'')}</span>
      </div>
      <div style="font-size:12px;">${esc(a.message)}</div>
      <div style="font-size:10px;color:var(--dim);margin-top:2px;">${esc(a.metric)}: ${esc(String(a.current_value||''))} (threshold: ${esc(String(a.threshold||''))})</div>
    </div>`;
  }).join('') : '<div class="empty">No performance alerts — all metrics within thresholds</div>');

  // Per-project analytics
  const ypData = projects.yallaplays;
  const fiData = projects.fionera;
  const miData = projects.mifteh;

  const ypVisits = (ypData?.overview?.monthly_visits || 0);
  const fiVisits = (fiData?.overview?.monthly_visits || 0);
  const miVisits = (miData?.overview?.monthly_visits || 0);

  set('analytics-yp-badge', `<span class="panel-badge badge-green">${fmtNum(ypVisits)}/mo</span>`);
  set('analytics-fi-badge', `<span class="panel-badge badge-blue">${fmtNum(fiVisits)}/mo</span>`);
  set('analytics-mi-badge', `<span class="panel-badge badge-dim">${fmtNum(miVisits)}/mo</span>`);

  set('analytics-yp-detail', projectAnalyticsBlock(ypData));
  set('analytics-fi-detail', projectAnalyticsBlock(fiData));
  set('analytics-mi-detail', projectAnalyticsBlock(miData));

  // Recommendations
  set('analytics-recs-badge', `<span class="panel-badge badge-green">${recs.length}</span>`);
  const typeIcon = { seo_page:'🔍', widget:'⚙', content:'✍️', cta_improvement:'🎯', metadata:'🏷', internal_links:'🔗', new_feature:'✨' };
  set('analytics-recommendations', recs.length ? recs.map((r, i) => `
    <div class="activity-item" style="align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--border);">
      <div style="font-size:20px;flex-shrink:0;width:32px;text-align:center;">${typeIcon[r.type]||'◻'}</div>
      <div class="activity-body" style="min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
          <span style="font-weight:700;font-size:13px;">${esc(r.title)}</span>
          ${priorityBadge(r.priority)}
          ${projectTag(r.project)}
        </div>
        <div style="font-size:12px;color:var(--muted);margin-bottom:4px;">${esc(r.description)}</div>
        <div style="font-size:11px;color:var(--dim);">
          📊 ${esc(r.rationale)}
        </div>
        <div style="display:flex;gap:16px;margin-top:6px;font-size:11px;">
          ${r.est_traffic_impact ? `<span style="color:var(--green);">+${fmtNum(r.est_traffic_impact)} visits/mo</span>` : ''}
          ${r.est_conversion_impact_pct ? `<span style="color:var(--cyan);">+${r.est_conversion_impact_pct?.toFixed(1)}% CVR</span>` : ''}
          <span style="color:var(--dim);">effort: ${esc(r.effort||'?')}</span>
          ${r.target_path ? `<code style="font-size:10px;color:var(--dim);">${esc(r.target_path)}</code>` : ''}
        </div>
      </div>
    </div>
  `).join('') : '<div class="empty">No recommendations yet — run Analytics Intelligence workflow</div>');

  // Decision queue
  set('analytics-queue-badge', `<span class="panel-badge badge-cyan">${queue.length}</span>`);
  set('analytics-queue', queue.length ? queue.map(dec => `
    <div class="pr-row" style="align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--border);">
      <div style="font-size:14px;font-weight:800;color:var(--purple);flex-shrink:0;width:24px;text-align:center;">#${dec.priority||'?'}</div>
      <div class="pr-body" style="min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
          ${projectTag(dec.project)}
          <span style="font-weight:700;font-size:12px;">${esc(dec.title)}</span>
          <span class="activity-badge badge-dim">${esc(dec.type?.replace(/_/g,' '))}</span>
          ${dec.auto_mergeable ? '<span class="activity-badge badge-green">auto-merge</span>' : ''}
        </div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:3px;">${esc(dec.rationale)}</div>
        <div style="display:flex;gap:12px;font-size:10px;color:var(--dim);">
          ${dec.target_file ? `<code>${esc(dec.target_file)}</code>` : ''}
          ${dec.estimated_impact?.monthly_visits ? `<span style="color:var(--green);">+${fmtNum(dec.estimated_impact.monthly_visits)} visits</span>` : ''}
          <span style="color:${dec.status==='queued'?'var(--yellow)':'var(--green)'};">${esc(dec.status||'queued')}</span>
        </div>
      </div>
    </div>
  `).join('') : '<div class="empty">Decision queue empty — run Analytics Intelligence to populate</div>');

  // Update execution summary
  const summary = ai.execution_summary;
  if (summary) {
    const el = document.getElementById('analytics-queue');
    if (el) el.insertAdjacentHTML('beforeend', `
      <div style="margin-top:12px;padding:10px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;color:var(--muted);border-left:2px solid var(--purple);">
        <strong style="color:var(--purple);">AI Strategy:</strong> ${esc(summary)}
      </div>
    `);
  }
}

// ─── Product Execution ───────────────────────────────────────────────────────

function featureTypeIcon(type) {
  const m = { category_page: '📄', seo_hub: '🔍', page: '🌐', widget: '⚙', component: '🧩' };
  return m[type] || '◻';
}

function featureTypeColor(type) {
  const m = { category_page: 'var(--green)', seo_hub: 'var(--cyan)', page: 'var(--blue)', widget: 'var(--purple)', component: 'var(--orange)' };
  return m[type] || 'var(--dim)';
}

function renderProduct(d) {
  const pm = d.product || {};
  const recent = pm.recent_features || [];

  const totalPages = pm.pages_generated || 0;
  const totalWidgets = pm.widgets_generated || 0;
  const estVisits = pm.est_monthly_seo_visits || 0;
  const totalFeatures = pm.total_features || 0;

  set('product-overview-cards',
    card('Total Features', totalFeatures, 'green', 'AI-generated') +
    card('Pages Created', totalPages, 'blue', 'SEO-optimized') +
    card('Widgets Built', totalWidgets, 'purple', 'interactive') +
    card('Est. Monthly SEO', estVisits.toLocaleString(), 'cyan', 'organic visits') +
    card('AI Cost', `$${(pm.total_cost_usd || 0).toFixed(5)}`, 'orange', `${(pm.total_tokens||0).toLocaleString()} tokens`) +
    card('Tokens Used', (pm.total_tokens||0).toLocaleString(), 'dim', 'product generation')
  );

  const byProject = pm.by_project || {};
  const byType = pm.by_type || {};

  function featureList(projectKey) {
    const items = recent.filter(f => f.project === projectKey);
    if (!items.length) return '<div class="empty">No features generated yet — run Feature Builder workflow</div>';
    return items.map(f => `
      <div class="activity-item" style="align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--border);">
        <div class="activity-icon" style="background:var(--surface2);color:${featureTypeColor(f.feature_type)};font-size:16px;">
          ${featureTypeIcon(f.feature_type)}
        </div>
        <div class="activity-body" style="min-width:0;">
          <div class="activity-title" style="font-size:13px;">${esc(f.label)}</div>
          <div class="activity-meta">
            <code style="font-size:10px;color:var(--dim);">${esc(f.target_path)}</code>
            ${f.seo_target ? `<span style="color:var(--cyan);margin-left:8px;">🔍 ${esc(f.seo_target)}</span>` : ''}
          </div>
          <div class="activity-meta" style="margin-top:2px;">
            ${f.est_monthly_visits ? `<span style="color:var(--green);">+${f.est_monthly_visits.toLocaleString()} visits/mo</span> · ` : ''}
            ${f.bytes_generated ? `${Math.round(f.bytes_generated/1024)}KB · ` : ''}
            ${relTime(f.generated_at)}
            ${f.pr_url ? `· <a href="${esc(f.pr_url)}" target="_blank" style="color:var(--blue);">PR ↗</a>` : ''}
          </div>
        </div>
        <span class="activity-badge" style="background:var(--surface2);color:${featureTypeColor(f.feature_type)};flex-shrink:0;">${esc(f.feature_type?.replace(/_/g,' '))}</span>
      </div>
    `).join('');
  }

  const ypCount = byProject.yallaplays || 0;
  const fiCount = byProject.fionera || 0;
  const miCount = byProject.mifteh || 0;

  set('product-yp-badge', `<span class="panel-badge badge-green">${ypCount} features</span>`);
  set('product-fi-badge', `<span class="panel-badge badge-blue">${fiCount} features</span>`);
  set('product-mi-badge', `<span class="panel-badge badge-dim">${miCount} features</span>`);

  set('product-yp-list', featureList('yallaplays'));
  set('product-fi-list', featureList('fionera'));
  set('product-mi-list', featureList('mifteh'));

  // Timeline
  set('product-timeline-badge', `<span class="panel-badge badge-dim">${recent.length} events</span>`);
  set('product-timeline', recent.length ? recent.map(f => `
    <div class="activity-item">
      <div class="activity-icon" style="background:var(--surface2);color:${featureTypeColor(f.feature_type)};">
        ${featureTypeIcon(f.feature_type)}
      </div>
      <div class="activity-body">
        <div class="activity-title">${projectTag(f.project)} ${esc(f.label)}</div>
        <div class="activity-meta">
          ${esc(f.feature_type?.replace(/_/g,' '))} · <code style="font-size:10px;">${esc(f.target_path)}</code>
          ${f.est_monthly_visits ? ` · <span style="color:var(--green);">+${f.est_monthly_visits.toLocaleString()} visits/mo</span>` : ''}
          · ${relTime(f.generated_at)}
        </div>
      </div>
      <span class="activity-badge badge-green">AI</span>
    </div>
  `).join('') : '<div class="empty">No product features generated yet. Run "Feature Builder" workflow to start.</div>');
}

// ─── Trust & Apply History ───────────────────────────────────────────────────

function trustBar(score) {
  const pct = Math.max(0, Math.min(100, score || 0));
  const color = pct >= 80 ? 'var(--green)' : pct >= 60 ? 'var(--yellow)' : 'var(--red)';
  return `<div style="display:flex;align-items:center;gap:8px;min-width:0;">
    <div style="flex:1;height:6px;background:var(--surface2);border-radius:3px;min-width:60px;">
      <div style="width:${pct}%;height:100%;background:${color};border-radius:3px;transition:width .3s;"></div>
    </div>
    <span style="color:${color};font-weight:700;font-size:13px;flex-shrink:0;">${pct}</span>
  </div>`;
}

function renderTrust(d) {
  const trust = d.trust || {};
  const repos = trust.repos || {};
  const cats = trust.categories || {};
  const suspended = trust.suspended_repos || [];
  const applyHistory = d.apply_history || [];
  const validationHistory = d.validation_history || [];

  // Overview cards
  const repoScores = Object.values(repos).map(r => r.score || 0);
  const avgRepoScore = repoScores.length ? Math.round(repoScores.reduce((a, b) => a + b, 0) / repoScores.length) : 0;
  const merged = applyHistory.filter(e => e.action === 'merged').length;
  const rejected = applyHistory.filter(e => e.action === 'rejected').length;
  set('trust-overview-cards',
    card('Avg Repo Trust', avgRepoScore, avgRepoScore >= 80 ? 'green' : 'yellow', 'score / 100') +
    card('Repos Active', Object.keys(repos).length - suspended.length, 'cyan', `${suspended.length} suspended`) +
    card('Total Merged', merged, 'green', 'auto-applied') +
    card('Rejected', rejected, 'yellow', 'below score 90') +
    card('Validations', validationHistory.length, 'blue', 'site checks') +
    card('Suspended', suspended.length, suspended.length ? 'red' : 'dim', suspended.length ? 'action required' : 'none')
  );

  // Repo trust
  set('trust-repos-badge', `<span class="panel-badge badge-dim">${Object.keys(repos).length} repos</span>`);
  set('trust-repos-list', Object.keys(repos).length ? Object.entries(repos).map(([repo, stats]) => {
    const isSuspended = suspended.includes(repo);
    return `<div class="output-row" style="flex-direction:column;align-items:stretch;gap:6px;padding:10px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-weight:600;font-size:13px;color:${isSuspended ? 'var(--red)' : 'var(--text)'};">
          ${isSuspended ? '⛔ ' : ''}${esc(repo.split('/')[1])}
        </span>
        <span style="font-size:11px;color:var(--muted);">${esc(repo)}</span>
      </div>
      ${trustBar(stats.score)}
      <div style="display:flex;gap:16px;font-size:11px;color:var(--dim);">
        <span>✅ ${stats.deploys || 0} deploys</span>
        <span>⏪ ${stats.rollbacks || 0} rollbacks</span>
        <span>❌ ${stats.failures || 0} failures</span>
        ${isSuspended ? '<span style="color:var(--red);font-weight:700;">SUSPENDED</span>' : ''}
      </div>
    </div>`;
  }).join('') : '<div class="empty">No trust data yet</div>');

  // Category trust
  set('trust-cats-list', Object.keys(cats).length ? Object.entries(cats).map(([cat, stats]) => `
    <div class="output-row" style="flex-direction:column;align-items:stretch;gap:4px;padding:8px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;">
        <span style="font-size:12px;font-weight:600;">${esc(cat.replace(/_/g, ' '))}</span>
        <span style="font-size:10px;color:var(--dim);">${stats.deploys || 0} deploys</span>
      </div>
      ${trustBar(stats.score)}
    </div>
  `).join('') : '<div class="empty">No category data yet</div>');

  // Apply history
  set('apply-history-badge', `<span class="panel-badge badge-dim">${applyHistory.length} events</span>`);
  const actionColor = { merged: 'var(--green)', rejected: 'var(--yellow)', merge_failed: 'var(--red)', skipped: 'var(--dim)', already_merged: 'var(--cyan)' };
  const actionIcon = { merged: '✅', rejected: '🚫', merge_failed: '❌', skipped: '–', already_merged: '✓' };
  set('apply-history-list', applyHistory.length ? [...applyHistory].reverse().map(e => `
    <div class="activity-item" style="align-items:flex-start;">
      <div class="activity-icon" style="background:var(--surface2);color:${actionColor[e.action] || 'var(--dim)'};">
        ${actionIcon[e.action] || '?'}
      </div>
      <div class="activity-body">
        <div class="activity-title">
          <span style="color:${actionColor[e.action] || 'var(--dim)'};">${esc(e.action?.replace(/_/g, ' ').toUpperCase())}</span>
          — ${esc(e.repo?.split('/')[1])} PR #${e.pr_number}
          ${e.pr_url ? `<a href="${esc(e.pr_url)}" target="_blank" style="color:var(--blue);margin-left:6px;font-size:11px;">↗ PR</a>` : ''}
        </div>
        <div class="activity-meta">
          Score: <strong>${e.score || 0}/100</strong> · ${esc(e.reason)} · ${relTime(e.evaluated_at)}
          ${e.merge_sha ? `· sha:${esc((e.merge_sha||'').slice(0,8))}` : ''}
        </div>
      </div>
    </div>
  `).join('') : '<div class="empty">No apply events yet — auto-merge runs daily at 07:00 UTC</div>');

  // Validation history
  set('validation-history-list', validationHistory.length ? [...validationHistory].reverse().map(e => {
    const pct = e.total ? Math.round((e.passed / e.total) * 100) : 0;
    return `<div class="activity-item">
      <div class="activity-icon" style="background:var(--surface2);color:${e.ok ? 'var(--green)' : 'var(--red)'};">${e.ok ? '✓' : '✗'}</div>
      <div class="activity-body">
        <div class="activity-title">${esc(e.repo?.split('/')[1])} — <span style="color:${e.ok ? 'var(--green)' : 'var(--red)'};">${e.ok ? 'OK' : 'DEGRADED'}</span></div>
        <div class="activity-meta">${e.passed}/${e.total} checks (${pct}%) · ${esc(e.base_url)} · ${relTime(e.validated_at)}</div>
      </div>
    </div>`;
  }).join('') : '<div class="empty">No validation events yet</div>');
}

// ─── Roadmap ──────────────────────────────────────────────────────────────────

function renderRoadmap(d) {
  const rm = d.roadmap || {};
  const queue = rm.consolidated_priority_queue || [];
  const cross = rm.cross_project || {};

  // Overview cards
  const seoGaps = Object.values(rm.projects || {}).reduce((acc, p) => acc + (p.seo_gaps || []).length, 0);
  const featGaps = Object.values(rm.projects || {}).reduce((acc, p) => acc + (p.feature_gaps || []).length, 0);
  set('roadmap-overview-cards', [
    { label: 'Total Items', value: rm.total_items || queue.length, color: 'var(--cyan)' },
    { label: 'SEO Gaps', value: seoGaps, color: 'var(--yellow)' },
    { label: 'Feature Gaps', value: featGaps, color: 'var(--blue)' },
    { label: 'Quick Wins', value: Object.values(rm.projects || {}).reduce((a, p) => a + (p.quick_wins || []).length, 0), color: 'var(--green)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  // Priority queue
  set('roadmap-queue-badge', `<span class="panel-badge badge-dim">${queue.length} items</span>`);
  const priorityColor = { critical: 'var(--red)', high: 'var(--yellow)', medium: 'var(--cyan)', low: 'var(--dim)' };
  set('roadmap-priority-queue', queue.length ? queue.slice(0, 15).map((item, i) => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border);display:flex;gap:12px;align-items:flex-start;">
      <span style="font-size:18px;font-weight:800;color:var(--dim);min-width:24px;">${i + 1}</span>
      <div style="flex:1;">
        <div style="font-weight:600;font-size:13px;">${esc(item.item || item.recommendation || '')}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:2px;">
          ${esc(item.project || '')} · ${esc(item.type || item.action_type || '')}
          ${item.estimated_traffic_impact ? ` · <span style="color:var(--green);">+${(item.estimated_traffic_impact||0).toLocaleString()} visits/mo</span>` : ''}
          ${item.roi_score ? ` · ROI ${item.roi_score}/100` : ''}
        </div>
        <div style="font-size:11px;color:var(--dim);">${esc(item.action || '')}</div>
      </div>
      <span style="font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid ${priorityColor[item.priority]||'var(--dim)'};color:${priorityColor[item.priority]||'var(--dim)'};flex-shrink:0;">${esc(item.priority || '')}</span>
    </div>
  `).join('') : '<div class="empty">No roadmap generated yet — run Roadmap Generator workflow</div>');

  // SEO gaps (first project)
  const firstProj = Object.values(rm.projects || {})[0] || {};
  const seoGapsList = firstProj.seo_gaps || [];
  set('roadmap-seo-badge', `<span class="panel-badge badge-yellow">${seoGapsList.length}</span>`);
  set('roadmap-seo-gaps', seoGapsList.slice(0, 6).map(g => `
    <div class="output-row">
      <span class="output-type-tag" style="background:${g.priority === 'high' ? '#7c3aed' : '#1d4ed8'}">${esc(g.priority || '?')}</span>
      <div>
        <div class="output-title">${esc(g.keyword || '')}</div>
        <div class="output-meta">${esc(g.recommended_page || '')} · ~${(g.est_monthly_volume||0).toLocaleString()} vol/mo</div>
      </div>
    </div>
  `).join('') || '<div class="empty">Run roadmap generation to detect SEO gaps</div>');

  // Feature gaps
  const featGapsList = firstProj.feature_gaps || [];
  set('roadmap-feature-gaps', featGapsList.slice(0, 5).map(g => `
    <div class="output-row">
      <span class="output-type-tag" style="background:var(--surface2);color:var(--cyan);">${esc(g.type || '?')}</span>
      <div>
        <div class="output-title">${esc(g.feature || '')}</div>
        <div class="output-meta">${esc(g.problem_solved || '')} · effort: ${esc(g.effort || '?')}</div>
      </div>
    </div>
  `).join('') || '<div class="empty">No feature gaps detected yet</div>');

  // Monetization
  const monOpp = firstProj.monetization_opportunities || [];
  set('roadmap-monetization', monOpp.slice(0, 4).map(m => `
    <div class="output-row">
      <span class="output-type-tag" style="background:#15803d;">${esc(m.type || '?')}</span>
      <div>
        <div class="output-title">${esc(m.opportunity || '')}</div>
        <div class="output-meta" style="color:var(--green);">~$${(m.est_monthly_revenue_usd||0).toLocaleString()}/mo · effort: ${esc(m.effort || '?')}</div>
      </div>
    </div>
  `).join('') || '<div class="empty">No monetization opportunities detected yet</div>');
}


// ─── Autonomous Executor ──────────────────────────────────────────────────────

function renderExecutor(d) {
  const exec = d.executor || {};
  const missions = exec.recent || [];

  const statusColor = { pr_created: 'var(--green)', dry_run_complete: 'var(--blue)', qa_blocked: 'var(--yellow)', generation_failed: 'var(--red)', plan_failed: 'var(--red)', commit_failed: 'var(--red)', error: 'var(--red)' };

  set('executor-overview-cards', [
    { label: 'Total Missions', value: exec.total || 0, color: 'var(--cyan)' },
    { label: 'Successful', value: exec.successful || 0, color: 'var(--green)' },
    { label: 'Failed', value: exec.failed || 0, color: exec.failed ? 'var(--red)' : 'var(--dim)' },
    { label: 'Success Rate', value: (exec.success_rate_pct || 0) + '%', color: 'var(--yellow)' },
    { label: 'Total Cost', value: '$' + (exec.total_cost_usd || 0).toFixed(4), color: 'var(--dim)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  set('executor-missions-badge', `<span class="panel-badge badge-dim">${missions.length} missions</span>`);
  set('executor-missions-list', missions.length ? [...missions].reverse().map(m => {
    const sc = statusColor[m.status] || 'var(--dim)';
    return `<div style="padding:12px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
        <div style="flex:1;">
          <div style="font-weight:600;font-size:13px;">${esc(m.feature_label || m.mission_id || '')}</div>
          <div style="font-size:11px;color:var(--dim);">${esc(m.project || '')} · ${relTime(m.started_at)}</div>
        </div>
        <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${sc}22;color:${sc};border:1px solid ${sc};flex-shrink:0;">${esc(m.status || '')}</span>
      </div>
      <div style="display:flex;gap:16px;font-size:11px;color:var(--dim);margin-top:4px;">
        <span>QA: ${m.qa_score || 0}/100</span>
        <span>Tokens: ${(m.tokens_used || 0).toLocaleString()}</span>
        <span>Cost: $${(m.cost_usd || 0).toFixed(5)}</span>
        ${m.pr_url ? `<a href="${esc(m.pr_url)}" target="_blank" style="color:var(--blue);">PR ↗</a>` : ''}
      </div>
    </div>`;
  }).join('') : '<div class="empty">No missions executed yet — run Autonomous Executor workflow</div>');
}


// ─── AI QA Engine ─────────────────────────────────────────────────────────────

function renderAIQA(d) {
  const qa = d.ai_qa || {};
  const reports = qa.reports || [];

  const decColor = { approve: 'var(--green)', review_required: 'var(--yellow)', block: 'var(--red)' };
  const readyColor = { ready: 'var(--green)', needs_minor_fixes: 'var(--yellow)', needs_major_rework: 'var(--red)' };

  set('aiqa-overview-cards', [
    { label: 'Reviewed', value: qa.total || 0, color: 'var(--cyan)' },
    { label: 'Approved', value: qa.approved || 0, color: 'var(--green)' },
    { label: 'Needs Review', value: qa.review_required || 0, color: 'var(--yellow)' },
    { label: 'Blocked', value: qa.blocked || 0, color: qa.blocked ? 'var(--red)' : 'var(--dim)' },
    { label: 'Avg AI Score', value: (qa.avg_ai_score || 0) + '/100', color: 'var(--blue)' },
    { label: 'Avg Composite', value: (qa.avg_composite_score || 0) + '/100', color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  set('aiqa-reviews-badge', `<span class="panel-badge badge-dim">${reports.length} reviews</span>`);
  set('aiqa-reviews-list', reports.length ? reports.map(r => {
    const dc = decColor[r.merge_decision] || 'var(--dim)';
    const rc = readyColor[r.production_readiness] || 'var(--dim)';
    const dims = r.dimension_scores || {};
    return `<div style="padding:14px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;">
        <div>
          <div style="font-weight:600;font-size:13px;">${esc(r.label || r.feature_id || '')}</div>
          <div style="font-size:11px;color:var(--dim);">${esc(r.project || '')} · AI: ${r.ai_score}/100 · Static: ${r.static_score}/100 · Composite: ${r.composite_score}/100</div>
        </div>
        <div style="display:flex;gap:6px;flex-shrink:0;">
          <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${dc}22;color:${dc};border:1px solid ${dc};">${esc(r.merge_decision || '')}</span>
          <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${rc}22;color:${rc};">${esc((r.production_readiness||'').replace(/_/g,' '))}</span>
        </div>
      </div>
      ${r.overall_critique ? `<div style="font-size:12px;color:var(--dim);font-style:italic;margin-bottom:6px;">"${esc(r.overall_critique)}"</div>` : ''}
      ${Object.keys(dims).length ? `<div style="display:flex;flex-wrap:wrap;gap:8px;font-size:11px;">
        ${Object.entries(dims).map(([k, v]) => `<span style="color:var(--dim);">${k.replace(/_/g,' ')}: <span style="color:${v >= 70 ? 'var(--green)' : v >= 50 ? 'var(--yellow)' : 'var(--red)'};">${v}</span></span>`).join('')}
      </div>` : ''}
      ${r.strengths && r.strengths.length ? `<div style="font-size:11px;color:var(--green);margin-top:4px;">✓ ${r.strengths.slice(0,2).map(s => esc(s)).join(' · ')}</div>` : ''}
      ${r.top_recommendations && r.top_recommendations.length ? `<div style="font-size:11px;color:var(--yellow);margin-top:4px;">→ ${r.top_recommendations[0]?.fix || ''}</div>` : ''}
    </div>`;
  }).join('') : '<div class="empty">No AI QA reviews yet — run AI QA Engine workflow</div>');
}


// ─── Browser Runtime ──────────────────────────────────────────────────────────

function renderBrowser(d) {
  const bqa = d.browser_qa || {};
  const reports = bqa.reports || [];
  const engine = bqa.engine || 'unknown';
  const pwAvail = bqa.playwright_available;

  set('browser-overview-cards', [
    { label: 'Engine', value: pwAvail ? 'Playwright' : 'Static', color: pwAvail ? 'var(--green)' : 'var(--yellow)' },
    { label: 'Validated', value: bqa.total || 0, color: 'var(--cyan)' },
    { label: 'Passing', value: bqa.passing || 0, color: 'var(--green)' },
    { label: 'Avg Score', value: (bqa.avg_score || 0) + '/100', color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  set('browser-reports-badge', `<span class="panel-badge badge-dim">${reports.length} reports</span>`);
  set('browser-reports-list', reports.length ? reports.map(r => {
    const gc = _qaGradeColor(r.grade);
    const shots = r.screenshots || {};
    return `<div style="padding:12px 0;border-bottom:1px solid var(--border);">
      <div style="display:flex;gap:10px;align-items:flex-start;">
        <span style="font-size:22px;font-weight:800;color:${gc};min-width:28px;">${r.grade}</span>
        <div style="flex:1;">
          <div style="font-weight:600;font-size:13px;">${esc(r.label || r.feature_id || '')}</div>
          <div style="font-size:11px;color:var(--dim);">${esc(r.project)} · ${r.score}/100 · engine: ${esc(r.engine || '')} · ${relTime(r.validated_at)}</div>
          <div style="display:flex;gap:16px;font-size:11px;color:var(--dim);margin-top:4px;">
            <span>CLS: ${(r.cls_score || 0).toFixed(2)}</span>
            <span>Console errors: ${r.console_errors || 0}</span>
            <span>Broken interactions: ${(r.interactions || {}).broken_interactions || 0}</span>
          </div>
          ${r.issues && r.issues.length ? `<div style="font-size:11px;color:var(--yellow);margin-top:4px;">${r.issues.slice(0,2).map(i => `• ${esc(i)}`).join(' ')}</div>` : ''}
        </div>
        ${shots.desktop_viewport ? `<img src="${esc(shots.desktop_viewport)}" style="width:80px;height:50px;object-fit:cover;border-radius:4px;border:1px solid var(--border);" onerror="this.style.display='none'" alt="desktop preview">` : ''}
        ${shots.mobile_viewport ? `<img src="${esc(shots.mobile_viewport)}" style="width:30px;height:50px;object-fit:cover;border-radius:4px;border:1px solid var(--border);" onerror="this.style.display='none'" alt="mobile preview">` : ''}
      </div>
    </div>`;
  }).join('') : `<div class="empty">No browser validation yet${pwAvail ? '' : ' — Playwright not installed in this environment'}. Run Browser Runtime workflow.</div>`);
}


// ─── Deployment Monitor ───────────────────────────────────────────────────────

function renderMonitor(d) {
  const mon = d.deployment_monitor || {};
  const sites = mon.sites || {};
  const allUp = mon.all_up;

  // Overview cards
  const siteList = Object.values(sites);
  const upCount = siteList.filter(s => s.uptime).length;
  const avgScore = siteList.length ? Math.round(siteList.reduce((a, s) => a + s.score, 0) / siteList.length) : 0;
  const avgSeo = siteList.length ? Math.round(siteList.reduce((a, s) => a + (s.seo_score || 0), 0) / siteList.length) : 0;

  set('monitor-overview-cards', [
    { label: 'Sites Up', value: `${upCount}/${siteList.length}`, color: upCount === siteList.length ? 'var(--green)' : 'var(--red)' },
    { label: 'Avg Score', value: avgScore + '/100', color: avgScore >= 70 ? 'var(--green)' : 'var(--yellow)' },
    { label: 'Avg SEO', value: avgSeo + '/100', color: 'var(--blue)' },
    { label: 'Status', value: allUp ? 'ALL UP' : 'DEGRADED', color: allUp ? 'var(--green)' : 'var(--red)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  function siteDetail(projKey, elId, badgeId) {
    const s = sites[projKey];
    if (!s) { set(elId, '<div class="empty">No data yet</div>'); return; }
    const statusColor = s.uptime ? 'var(--green)' : 'var(--red)';
    const cwv = s.cwv || {};
    const critPages = s.critical_pages || {};
    set(badgeId, `<span class="panel-badge ${s.ok ? 'badge-green' : 'badge-yellow'}">${s.ok ? 'healthy' : 'degraded'}</span>`);
    set(elId, `
      <div style="display:flex;gap:16px;flex-wrap:wrap;padding:8px 0;font-size:12px;">
        <span>Status: <span style="color:${statusColor};font-weight:700;">HTTP ${s.status_code}</span></span>
        <span>TTFB: ${s.ttfb_ms}ms</span>
        <span>Score: ${s.score}/100 (${s.grade})</span>
        <span>SEO: ${s.seo_score}/100 (${s.seo_grade})</span>
        <span>30d uptime: ${s.uptime_30d_pct || 100}%</span>
      </div>
      <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:11px;color:var(--dim);">
        <span>LCP: <span style="color:${cwv.lcp_grade === 'good' ? 'var(--green)' : 'var(--yellow)'};">${cwv.lcp_grade || '?'}</span> (~${cwv.lcp_ms_estimate || 0}ms)</span>
        <span>CLS: <span style="color:${cwv.cls_grade === 'good' ? 'var(--green)' : 'var(--yellow)'};">${cwv.cls_grade || '?'}</span></span>
        <span>FID: <span style="color:${cwv.fid_grade === 'good' ? 'var(--green)' : 'var(--yellow)'};">${cwv.fid_grade || '?'}</span></span>
      </div>
      ${Object.keys(critPages).length ? `<div style="font-size:11px;color:var(--dim);margin-top:6px;">
        ${Object.entries(critPages).map(([pg, v]) => `<span style="margin-right:12px;">${esc(pg)}: <span style="color:${v.ok ? 'var(--green)' : 'var(--red)'};">${v.status}</span></span>`).join('')}
      </div>` : ''}
      ${s.issues && s.issues.length ? `<div style="font-size:11px;color:var(--yellow);margin-top:6px;">${s.issues.map(i => `• ${esc(i)}`).join(' ')}</div>` : ''}
    `);
  }

  siteDetail('yallaplays', 'monitor-yp-detail', 'monitor-yp-badge');
  siteDetail('fionera',    'monitor-fi-detail', 'monitor-fi-badge');
  siteDetail('mifteh',     'monitor-mi-detail', 'monitor-mi-badge');
}


// ─── Memory ───────────────────────────────────────────────────────────────────

function renderMemory(d) {
  const mem = d.memory || {};

  set('memory-overview-cards', [
    { label: 'Total Memories', value: mem.total_memories || 0, color: 'var(--cyan)' },
    { label: 'Successes', value: mem.total_successes || 0, color: 'var(--green)' },
    { label: 'Failures', value: mem.total_failures || 0, color: mem.total_failures ? 'var(--yellow)' : 'var(--dim)' },
    { label: 'Success Rate', value: (mem.success_rate_pct || 0) + '%', color: 'var(--green)' },
    { label: 'Avg QA Score', value: (mem.avg_qa_score || 0) + '/100', color: 'var(--blue)' },
    { label: 'Prompts Tracked', value: mem.prompt_count || 0, color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  // Success patterns
  const patterns = mem.success_patterns || [];
  set('memory-success-badge', `<span class="panel-badge badge-green">${patterns.length}</span>`);
  set('memory-success-list', patterns.length ? patterns.map(p => `
    <div class="output-row">
      <span style="color:var(--green);font-size:16px;">✓</span>
      <div class="output-title">${esc(p)}</div>
    </div>
  `).join('') + (mem.recent ? mem.recent.filter(r => r.type === 'success').slice(0, 5).map(r => `
    <div class="output-row">
      <span class="output-type-tag" style="background:var(--surface2);color:var(--green);">${esc(r.project || '')}</span>
      <div>
        <div class="output-title">${esc(r.label || r.feature_id || '')}</div>
        <div class="output-meta">QA: ${r.qa_score || 0}/100 · ${relTime(r.recorded_at)}</div>
      </div>
    </div>
  `).join('') : '') : '<div class="empty">No successes recorded yet — run memory sync after first successful generation</div>');

  // Failure patterns / learnings
  const improvements = mem.priority_improvements || [];
  set('memory-failure-badge', `<span class="panel-badge badge-yellow">${improvements.length}</span>`);
  set('memory-failure-list', improvements.length ? improvements.map(p => `
    <div class="output-row">
      <span style="color:var(--yellow);font-size:16px;">→</span>
      <div class="output-title">${esc(p)}</div>
    </div>
  `).join('') + (mem.recent ? mem.recent.filter(r => r.type === 'failure').slice(0, 4).map(r => `
    <div class="output-row">
      <span class="output-type-tag" style="background:var(--surface2);color:var(--red);">FAIL</span>
      <div>
        <div class="output-title">${esc(r.label || r.feature_id || '')}</div>
        <div class="output-meta">${esc(r.project || '')} · ${relTime(r.recorded_at)}</div>
      </div>
    </div>
  `).join('') : '') : '<div class="empty">No failure patterns yet</div>');

  // Top prompts
  const prompts = mem.top_prompts || [];
  set('memory-prompts-badge', `<span class="panel-badge badge-cyan">${prompts.length}</span>`);
  set('memory-prompts-list', prompts.length ? prompts.map(p => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border);display:flex;gap:12px;align-items:center;">
      <div style="flex:1;">
        <div style="font-weight:600;font-size:12px;font-family:monospace;">${esc(p.prompt_key || '')}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:2px;">${p.runs || 0} runs · ${p.success_rate || 0}% success</div>
      </div>
      <div style="text-align:right;">
        <div style="font-weight:700;color:${(p.avg_qa_score||0) >= 70 ? 'var(--green)' : 'var(--yellow)'};">${p.avg_qa_score || 0}/100</div>
        <div style="font-size:11px;color:var(--dim);">avg QA</div>
      </div>
    </div>
  `).join('') : '<div class="empty">No prompt performance data yet</div>');

  // Latest learning
  const latestLearning = mem.latest_learning || '';
  set('memory-learnings-detail', latestLearning
    ? `<div style="padding:16px;background:#0f1929;border-radius:8px;border-left:3px solid var(--cyan);">
        <div style="font-size:13px;font-weight:600;margin-bottom:8px;">Key Insight</div>
        <div style="font-size:12px;color:var(--text);">${esc(latestLearning)}</div>
        ${mem.learning_count ? `<div style="font-size:11px;color:var(--dim);margin-top:8px;">${mem.learning_count} total learning cycles</div>` : ''}
      </div>`
    : '<div class="empty">Run Memory Sync with AI synthesis to generate learnings</div>');
}


// ─── Revenue ─────────────────────────────────────────────────────────────────

function renderRevenue(d) {
  const rev = d.revenue || {};
  const ps = rev.portfolio_summary || {};
  const ai = rev.ai_analysis || {};
  const projects = rev.projects || {};

  set('revenue-cards', [
    { label: 'Portfolio Value/mo', value: '$' + (ps.total_est_value_usd || 0).toFixed(2), color: 'var(--green)' },
    { label: 'Token ROI', value: (ps.portfolio_roi || 0).toFixed(1) + 'x', color: 'var(--cyan)' },
    { label: '30d Forecast', value: '$' + (ps['30d_forecast_usd'] || 0).toFixed(2), color: 'var(--blue)' },
    { label: '90d Forecast', value: '$' + (ps['90d_forecast_usd'] || 0).toFixed(2), color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  // Project breakdown
  set('revenue-projects', Object.entries(projects).map(([proj, data]) => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-weight:600;text-transform:uppercase;font-size:11px;color:var(--cyan)">${esc(proj)}</span>
        <span style="font-size:12px;color:var(--dim)">${esc(data.monetization_model || '')}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
        <div style="background:var(--bg2);padding:8px;border-radius:6px;text-align:center">
          <div style="font-size:14px;font-weight:700;color:var(--green)">$${(data.total_estimated_value_usd || 0).toFixed(2)}</div>
          <div style="font-size:10px;color:var(--dim)">Value/mo</div>
        </div>
        <div style="background:var(--bg2);padding:8px;border-radius:6px;text-align:center">
          <div style="font-size:14px;font-weight:700;color:var(--cyan)">${(data.portfolio_roi || 0).toFixed(1)}x</div>
          <div style="font-size:10px;color:var(--dim)">Token ROI</div>
        </div>
        <div style="background:var(--bg2);padding:8px;border-radius:6px;text-align:center">
          <div style="font-size:14px;font-weight:700;color:var(--yellow)">${(data.traffic_growth_pct || 0).toFixed(1)}%</div>
          <div style="font-size:10px;color:var(--dim)">Traffic Growth</div>
        </div>
      </div>
    </div>`).join('') || '<div style="padding:20px;color:var(--dim);text-align:center">No revenue data yet — run revenue engine</div>');

  // Opportunities
  const opps = ai.revenue_opportunities || [];
  set('revenue-opportunities', opps.length ? opps.map(o => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:13px">${esc(o.opportunity || '')}</span>
        <span style="color:var(--green);font-size:12px;font-weight:700">+$${(o.est_monthly_uplift_usd || 0).toFixed(0)}/mo</span>
      </div>
      <div style="font-size:11px;color:var(--dim);margin-top:3px">${esc(o.project || '')} · ${esc(o.effort || '')} effort</div>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">Run revenue engine for opportunities</div>');

  // Top ROI features across all projects
  const allFeatures = Object.values(projects).flatMap(p => p.top_roi_features || []);
  allFeatures.sort((a, b) => b.roi_ratio - a.roi_ratio);
  set('revenue-features', allFeatures.length ? `
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="border-bottom:1px solid var(--border);color:var(--dim)">
        <th style="text-align:left;padding:6px 0">Feature</th>
        <th style="text-align:right;padding:6px">Visits/mo</th>
        <th style="text-align:right;padding:6px">SEO Value</th>
        <th style="text-align:right;padding:6px">Revenue</th>
        <th style="text-align:right;padding:6px">ROI</th>
      </tr></thead>
      <tbody>${allFeatures.slice(0, 10).map(f => `<tr style="border-bottom:1px solid var(--border)">
        <td style="padding:7px 0"><div style="font-weight:500">${esc(f.feature_id || '')}</div><div style="font-size:10px;color:var(--dim)">${esc(f.project || '')} · ${esc(f.feature_type || '')}</div></td>
        <td style="text-align:right;padding:7px">${(f.est_monthly_visits || 0).toLocaleString()}</td>
        <td style="text-align:right;padding:7px;color:var(--green)">$${(f.seo_value_usd || 0).toFixed(2)}</td>
        <td style="text-align:right;padding:7px;color:var(--cyan)">$${(f.direct_revenue_usd || 0).toFixed(2)}</td>
        <td style="text-align:right;padding:7px;color:var(--yellow);font-weight:700">${(f.roi_ratio || 0).toFixed(0)}x</td>
      </tr>`).join('')}</tbody>
    </table>` : '<div style="padding:16px;color:var(--dim)">No feature revenue data yet</div>');

  if (ai.key_insight) {
    const el = document.getElementById('revenue-projects-panel');
    if (el) {
      const tip = document.createElement('div');
      tip.style.cssText = 'padding:10px;background:var(--bg2);border-left:3px solid var(--cyan);margin-top:12px;font-size:12px;border-radius:0 6px 6px 0';
      tip.textContent = '💡 ' + ai.key_insight;
      el.appendChild(tip);
    }
  }
}

// ─── Swarm ────────────────────────────────────────────────────────────────────

function renderSwarm(d) {
  const sw = d.swarm || {};
  const missions = sw.recent_missions || [];

  set('swarm-cards', [
    { label: 'Total Missions', value: sw.total_missions || 0, color: 'var(--cyan)' },
    { label: 'Agents per Mission', value: '6', color: 'var(--blue)' },
    { label: 'Active Projects', value: new Set(missions.map(m => m.project)).size || 0, color: 'var(--green)' },
    { label: 'High Priority Plans', value: missions.filter(m => m.execution_priority === 'high').length, color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  const priorityColor = { high: 'var(--red)', medium: 'var(--yellow)', low: 'var(--dim)' };
  set('swarm-missions', missions.length ? missions.map(m => {
    const plan = m.implementation_plan || {};
    const impact = m.estimated_30d_impact || plan.estimated_30d_impact || {};
    const proposals = m.top_proposals || [];
    return `<div style="background:var(--bg2);border-radius:8px;padding:16px;margin-bottom:12px;border-left:3px solid var(--cyan)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div>
          <div style="font-weight:700;font-size:14px">${esc(plan.plan_title || m.mission || '')}</div>
          <div style="font-size:11px;color:var(--dim);margin-top:2px">
            ${esc(m.project || '')} · ${(m.agents_used || []).length} agents · ${esc(m.generated_at ? m.generated_at.slice(0,10) : '')}
          </div>
        </div>
        <span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;background:var(--bg3);color:${priorityColor[m.execution_priority] || 'var(--dim)'}">${(m.execution_priority || '').toUpperCase()}</span>
      </div>
      ${plan.plan_summary ? `<div style="font-size:12px;color:var(--fg2);margin-bottom:10px">${esc(plan.plan_summary)}</div>` : ''}
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px">
        <div style="background:var(--bg3);padding:6px;border-radius:6px;text-align:center">
          <div style="font-size:13px;font-weight:700;color:var(--green)">+${impact.traffic_increase_pct || 0}%</div>
          <div style="font-size:10px;color:var(--dim)">Traffic</div>
        </div>
        <div style="background:var(--bg3);padding:6px;border-radius:6px;text-align:center">
          <div style="font-size:13px;font-weight:700;color:var(--cyan)">$${impact.revenue_increase_usd || 0}</div>
          <div style="font-size:10px;color:var(--dim)">Revenue</div>
        </div>
        <div style="background:var(--bg3);padding:6px;border-radius:6px;text-align:center">
          <div style="font-size:13px;font-weight:700;color:var(--blue)">+${impact.seo_score_improvement || 0}</div>
          <div style="font-size:10px;color:var(--dim)">SEO pts</div>
        </div>
      </div>
      ${proposals.length ? `<div style="font-size:11px;color:var(--dim);margin-bottom:6px">TOP PROPOSALS</div>
      ${proposals.slice(0,3).map(p => `<div style="padding:6px 0;border-top:1px solid var(--border);font-size:12px">
        <span style="font-weight:600">${esc(p.title || '')}</span>
        <span style="color:var(--dim);margin-left:8px">${esc(p.source_role || '')}</span>
        <span style="float:right;color:var(--cyan)">${p.confidence || 0}% conf</span>
      </div>`).join('')}` : ''}
    </div>`;
  }).join('') : '<div style="padding:40px;text-align:center;color:var(--dim)">No swarm missions yet — run the Swarm Orchestrator workflow</div>');
}

// ─── Strategy ─────────────────────────────────────────────────────────────────

function renderStrategy(d) {
  const st = d.strategy || {};
  const plan = st.strategic_plan || {};
  const d30 = plan['30_day_plan'] || {};
  const d90 = plan['90_day_plan'] || {};
  const bottlenecks = st.bottlenecks || [];
  const matrix = plan.priority_matrix || [];
  const forecasts = plan.roi_forecasts || {};

  set('strategy-cards', [
    { label: 'North Star', value: (plan.north_star_metric || 'N/A').slice(0,18), color: 'var(--yellow)' },
    { label: '30d Traffic', value: '+' + (d30.projected_traffic_growth_pct || 0) + '%', color: 'var(--green)' },
    { label: '90d Revenue', value: '$' + (d90.projected_revenue_growth_usd || 0), color: 'var(--cyan)' },
    { label: 'ROI Mult (90d)', value: (forecasts['90d_roi_multiplier'] || 0) + 'x', color: 'var(--blue)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  if (plan.strategic_summary) {
    const el = document.getElementById('strategy-30d');
    if (el) el.insertAdjacentHTML('beforebegin', `<div style="padding:12px;background:var(--bg2);border-left:3px solid var(--yellow);border-radius:0 6px 6px 0;margin-bottom:16px;font-size:13px">${esc(plan.strategic_summary)}</div>`);
  }

  // 30-day plan
  const inits30 = d30.key_initiatives || [];
  set('strategy-30d', `
    ${d30.theme ? `<div style="font-size:11px;font-weight:700;color:var(--cyan);margin-bottom:8px">THEME: ${esc(d30.theme)}</div>` : ''}
    ${(d30.objectives || []).map(o => `<div style="padding:4px 0;font-size:12px">• ${esc(o)}</div>`).join('')}
    ${inits30.length ? `<div style="margin-top:10px;font-size:11px;color:var(--dim)">KEY INITIATIVES</div>` : ''}
    ${inits30.slice(0,5).map(i => `
      <div style="padding:8px 0;border-bottom:1px solid var(--border)">
        <div style="font-weight:600;font-size:13px">${esc(i.initiative || '')}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:2px">
          ${esc(i.project || '')} · ${esc(i.effort || '')} effort · ${esc(i.owner || '')}
        </div>
        <div style="font-size:11px;color:var(--green);margin-top:2px">${esc(i.expected_impact || '')}</div>
      </div>`).join('')}`);

  // 90-day milestones
  const milestones = d90.milestones || [];
  set('strategy-90d', `
    ${d90.theme ? `<div style="font-size:11px;font-weight:700;color:var(--blue);margin-bottom:8px">THEME: ${esc(d90.theme)}</div>` : ''}
    ${milestones.map(m => `
      <div style="padding:10px;background:var(--bg2);border-radius:6px;margin-bottom:8px">
        <div style="font-size:10px;color:var(--dim);margin-bottom:4px">WEEK ${m.week}</div>
        <div style="font-weight:600;font-size:13px">${esc(m.milestone || '')}</div>
        <div style="font-size:11px;color:var(--cyan);margin-top:4px">${esc(m.metrics || '')}</div>
      </div>`).join('') || '<div style="color:var(--dim);padding:16px">Run strategy engine to generate milestones</div>'}`);

  // Bottlenecks
  const sevColor = { critical: 'var(--red)', high: 'var(--yellow)', medium: 'var(--cyan)', low: 'var(--dim)' };
  set('strategy-bottlenecks', bottlenecks.length ? bottlenecks.map(b => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border);display:flex;gap:10px;align-items:flex-start">
      <span style="padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;background:var(--bg2);color:${sevColor[b.severity] || 'var(--dim)'};white-space:nowrap">${(b.severity || '').toUpperCase()}</span>
      <div>
        <div style="font-size:13px;font-weight:600">${esc(b.issue || '')}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:2px">${esc(b.project || '')} · ${esc(b.impact || '')}</div>
      </div>
    </div>`).join('') : '<div style="padding:16px;color:var(--green)">No critical bottlenecks detected</div>');

  // Priority matrix
  const quadrantColor = { do_now: 'var(--green)', plan: 'var(--cyan)', delegate: 'var(--yellow)', drop: 'var(--dim)' };
  set('strategy-matrix', matrix.length ? matrix.slice(0,8).map(i => `
    <div style="padding:8px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:13px;font-weight:600">${esc(i.initiative || '')}</div>
        <div style="font-size:11px;color:var(--dim)">${esc(i.project || '')} · impact: ${esc(i.impact || '')} · effort: ${esc(i.effort || '')}</div>
      </div>
      <span style="padding:3px 10px;border-radius:10px;font-size:10px;font-weight:700;background:var(--bg2);color:${quadrantColor[i.quadrant] || 'var(--dim)'};white-space:nowrap">${(i.quadrant || '').replace('_',' ').toUpperCase()}</span>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">Run strategy engine for priority matrix</div>');
}

// ─── Market Intelligence ──────────────────────────────────────────────────────

function renderMarket(d) {
  const mk = d.market || {};
  const trends = mk.trending_topics || {};
  const kwGaps = mk.keyword_gaps || {};
  const competitors = mk.competitors || {};

  const totalTopics = Object.values(trends).reduce((a, t) => a + t.length, 0);
  const totalGaps = Object.values(kwGaps).reduce((a, g) => a + g.length, 0);
  const totalComps = Object.values(competitors).reduce((a, c) => a + c.length, 0);
  const reachable = Object.values(competitors).flat().filter(c => c.reachable).length;

  set('market-cards', [
    { label: 'Trending Topics', value: totalTopics, color: 'var(--cyan)' },
    { label: 'Keyword Gaps', value: totalGaps, color: 'var(--yellow)' },
    { label: 'Competitors Tracked', value: totalComps, color: 'var(--blue)' },
    { label: 'Competitors Reachable', value: reachable, color: 'var(--green)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  // Trending topics
  const trendColor = { rising: 'var(--green)', stable: 'var(--cyan)', declining: 'var(--red)' };
  const allTopics = Object.entries(trends).flatMap(([proj, list]) => list.map(t => ({...t, project: proj})));
  set('market-topics', allTopics.length ? allTopics.slice(0, 12).map(t => `
    <div style="padding:8px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:13px">${esc(t.topic || '')}</span>
        <span style="font-size:10px;color:${trendColor[t.search_trend] || 'var(--dim)'};font-weight:700">${(t.search_trend || '').toUpperCase()}</span>
      </div>
      <div style="font-size:11px;color:var(--dim);margin-top:2px">
        ${esc(t.project || '')} · ~${(t.est_monthly_searches || 0).toLocaleString()} searches/mo · ${esc(t.competition || '')} competition
      </div>
      <div style="font-size:11px;color:var(--cyan);margin-top:2px">${esc(t.opportunity || '')}</div>
    </div>`).join('') : '<div style="padding:20px;color:var(--dim);text-align:center">Run market intelligence to detect trends</div>');

  // Keyword gaps
  const allGaps = Object.entries(kwGaps).flatMap(([proj, list]) => list.map(g => ({...g, project: proj})));
  allGaps.sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0));
  set('market-keywords', allGaps.length ? allGaps.slice(0, 10).map(g => `
    <div style="padding:8px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:600;font-size:13px">${esc(g.keyword || '')}</span>
        <div style="display:flex;gap:6px;align-items:center">
          <div style="background:var(--bg2);border-radius:4px;padding:2px 0;width:60px;height:6px;overflow:hidden">
            <div style="background:var(--cyan);height:100%;width:${(g.opportunity_score || 0) * 10}%"></div>
          </div>
          <span style="font-size:11px;color:var(--cyan)">${g.opportunity_score || 0}/10</span>
        </div>
      </div>
      <div style="font-size:11px;color:var(--dim);margin-top:2px">
        ${esc(g.project || '')} · ~${(g.est_monthly_searches || 0).toLocaleString()} searches · coverage: ${esc(g.current_coverage || 'none')}
      </div>
    </div>`).join('') : '<div style="padding:20px;color:var(--dim)">No keyword gap data yet</div>');

  // Competitors
  const allComps = Object.entries(competitors).flatMap(([proj, list]) => list.map(c => ({...c, project: proj})));
  set('market-competitors', allComps.length ? `
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="border-bottom:1px solid var(--border);color:var(--dim)">
        <th style="text-align:left;padding:6px 0">Competitor</th>
        <th style="text-align:left;padding:6px">Project</th>
        <th style="text-align:center;padding:6px">Status</th>
        <th style="text-align:right;padding:6px">Words</th>
        <th style="text-align:center;padding:6px">Schema</th>
        <th style="text-align:right;padding:6px">Links</th>
      </tr></thead>
      <tbody>${allComps.map(c => `<tr style="border-bottom:1px solid var(--border)">
        <td style="padding:7px 0"><a href="${esc(c.url || '')}" target="_blank" style="color:var(--cyan);text-decoration:none">${esc(c.name || '')}</a></td>
        <td style="padding:7px;color:var(--dim)">${esc(c.project || '')}</td>
        <td style="text-align:center;padding:7px"><span style="color:${c.reachable ? 'var(--green)' : 'var(--red)'}">${c.reachable ? '●' : '○'}</span></td>
        <td style="text-align:right;padding:7px">${(c.content_word_count || 0).toLocaleString()}</td>
        <td style="text-align:center;padding:7px">${c.has_structured_data ? '✓' : '–'}</td>
        <td style="text-align:right;padding:7px">${c.internal_link_count || 0}</td>
      </tr>`).join('')}</tbody>
    </table>` : '<div style="padding:16px;color:var(--dim)">No competitor data yet</div>');
}

// ─── Priority Engine ──────────────────────────────────────────────────────────

function renderPriority(d) {
  const pr = d.priority || {};
  const mode = pr.execution_mode || 'balanced';
  const cfg = pr.mode_config || {};
  const decisions = pr.top_decisions || [];
  const weights = pr.score_weights || {};

  const modeColor = { safe: 'var(--blue)', balanced: 'var(--green)', aggressive: 'var(--yellow)', experimental: 'var(--red)' };

  set('priority-cards', [
    { label: 'Execution Mode', value: mode.toUpperCase(), color: modeColor[mode] || 'var(--cyan)' },
    { label: 'Queue Depth', value: pr.total_decisions || 0, color: 'var(--cyan)' },
    { label: 'Max Missions/Cycle', value: cfg.max_missions_per_cycle || 3, color: 'var(--blue)' },
    { label: 'Trust Threshold', value: (cfg.trust_threshold || 70) + '%', color: 'var(--green)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  set('priority-mode', `
    <div style="display:flex;gap:12px;flex-wrap:wrap">
      ${['safe','balanced','aggressive','experimental'].map(m => `
        <div style="flex:1;min-width:140px;padding:12px;background:var(--bg2);border-radius:8px;border:2px solid ${m === mode ? (modeColor[m] || 'var(--cyan)') : 'transparent'}">
          <div style="font-weight:700;font-size:13px;color:${modeColor[m] || 'var(--dim)'}">${m.toUpperCase()}</div>
          <div style="font-size:11px;color:var(--dim);margin-top:4px">${
            {safe:'Trust ≥85 · QA ≥75 · 2/cycle', balanced:'Trust ≥70 · QA ≥60 · 3/cycle', aggressive:'Trust ≥50 · QA ≥50 · 5/cycle', experimental:'Trust ≥40 · QA ≥45 · 8/cycle'}[m]
          }</div>
        </div>`).join('')}
    </div>
    <div style="margin-top:12px;padding:10px;background:var(--bg2);border-radius:6px">
      <div style="font-size:11px;color:var(--dim);margin-bottom:6px">SCORE WEIGHTS</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${Object.entries(weights).map(([k, v]) => `
          <div style="font-size:11px">
            <span style="color:var(--cyan)">${k.replace(/_/g,' ')}</span>
            <span style="color:var(--dim)"> ${((v||0)*100).toFixed(0)}%</span>
          </div>`).join('')}
      </div>
    </div>`);

  set('priority-queue', decisions.length ? decisions.map((d, i) => `
    <div style="padding:10px;background:var(--bg2);border-radius:6px;margin-bottom:8px;border-left:3px solid var(--cyan)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <div style="display:flex;gap:10px;align-items:center">
          <span style="font-size:20px;font-weight:800;color:var(--dim)">#${i+1}</span>
          <div>
            <div style="font-weight:600;font-size:13px">${esc(d.title || d.action || '')}</div>
            <div style="font-size:11px;color:var(--dim)">${esc(d.project || '')} · ${esc(d.type || d.feature_type || '')} · source: ${esc(d.source || '')}</div>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:18px;font-weight:800;color:var(--yellow)">${(d.priority_score || 0).toFixed(1)}</div>
          <div style="font-size:10px;color:var(--dim)">score</div>
        </div>
      </div>
      ${d.score_breakdown ? `<div style="display:flex;gap:6px;flex-wrap:wrap">
        ${Object.entries(d.score_breakdown).slice(0,4).map(([k, v]) => `
          <div style="font-size:10px;background:var(--bg3);padding:3px 7px;border-radius:10px">
            ${k.replace(/_/g,' ')}: <span style="color:var(--cyan)">${v}</span>
          </div>`).join('')}
      </div>` : ''}
    </div>`).join('') : '<div style="padding:20px;text-align:center;color:var(--dim)">No decisions in queue yet</div>');
}

// ─── Experiments ──────────────────────────────────────────────────────────────

function renderExperiments(d) {
  const ex = d.experiments || {};
  const byType = ex.by_type || {};
  const promote = ex.promote_recommended || [];
  const recent = ex.recent || [];

  set('experiments-cards', [
    { label: 'Total Experiments', value: ex.total || 0, color: 'var(--cyan)' },
    { label: 'Variant Win Rate', value: (ex.win_rate_pct || 0).toFixed(1) + '%', color: 'var(--green)' },
    { label: 'Avg Score Delta', value: (ex.avg_score_delta || 0) > 0 ? '+' + (ex.avg_score_delta || 0).toFixed(1) : (ex.avg_score_delta || 0).toFixed(1), color: ex.avg_score_delta > 0 ? 'var(--green)' : 'var(--red)' },
    { label: 'Ready to Promote', value: promote.length, color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  set('experiments-by-type', Object.entries(byType).length ? Object.entries(byType).map(([type, stats]) => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-weight:700;font-size:12px;text-transform:uppercase;color:var(--cyan)">${esc(type)}</span>
        <span style="font-size:11px;color:${stats.avg_delta > 0 ? 'var(--green)' : 'var(--red)'}">${stats.avg_delta > 0 ? '+' : ''}${(stats.avg_delta || 0).toFixed(1)} pts avg</span>
      </div>
      <div style="font-size:11px;color:var(--dim)">
        ${stats.total || 0} experiments · ${stats.variant_wins || 0} variant wins
        (${stats.total ? Math.round((stats.variant_wins/stats.total)*100) : 0}%)
      </div>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">Run experiment engine to see results by type</div>');

  set('experiments-promote', promote.length ? promote.map(e => `
    <div style="padding:10px;background:var(--bg2);border-radius:6px;margin-bottom:8px;border-left:3px solid var(--green)">
      <div style="font-weight:600;font-size:13px">${esc(e.feature_id || '')}</div>
      <div style="font-size:11px;color:var(--dim);margin-top:2px">
        ${esc(e.project || '')} · ${esc(e.experiment_type || '')}
      </div>
      <div style="font-size:12px;margin-top:4px">
        <span style="color:var(--dim)">Control: ${e.control_score || 0}</span>
        <span style="margin: 0 8px;color:var(--dim)">→</span>
        <span style="color:var(--green);font-weight:700">Variant: ${e.variant_score || 0} (+${e.score_delta || 0})</span>
      </div>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">No variants ready to promote yet</div>');

  set('experiments-recent', recent.length ? `
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr style="border-bottom:1px solid var(--border);color:var(--dim)">
        <th style="text-align:left;padding:6px 0">Feature</th>
        <th style="text-align:left;padding:6px">Type</th>
        <th style="text-align:center;padding:6px">Winner</th>
        <th style="text-align:right;padding:6px">Control</th>
        <th style="text-align:right;padding:6px">Variant</th>
        <th style="text-align:right;padding:6px">Delta</th>
      </tr></thead>
      <tbody>${recent.map(e => `<tr style="border-bottom:1px solid var(--border)">
        <td style="padding:7px 0"><div>${esc(e.feature_id || '')}</div><div style="font-size:10px;color:var(--dim)">${esc(e.project || '')}</div></td>
        <td style="padding:7px;color:var(--dim)">${esc(e.experiment_type || '')}</td>
        <td style="text-align:center;padding:7px">
          <span style="color:${e.winner === 'variant' ? 'var(--green)' : 'var(--dim)'};font-weight:700">${e.winner === 'variant' ? 'VARIANT' : 'CONTROL'}</span>
        </td>
        <td style="text-align:right;padding:7px">${e.control_score || 0}</td>
        <td style="text-align:right;padding:7px">${e.variant_score || 0}</td>
        <td style="text-align:right;padding:7px;color:${e.score_delta > 0 ? 'var(--green)' : 'var(--red)'};font-weight:600">${e.score_delta > 0 ? '+' : ''}${e.score_delta || 0}</td>
      </tr>`).join('')}</tbody>
    </table>` : '<div style="padding:16px;color:var(--dim)">No experiments run yet</div>');
}

// ─── Cross-Project Learning ───────────────────────────────────────────────────

function renderCrossLearn(d) {
  const cl = d.cross_project || {};
  const patterns = cl.top_patterns || [];
  const opps = cl.shared_opportunities || [];
  const insights = cl.project_insights || {};
  const prompts = cl.reusable_prompts || [];

  set('crosslearn-cards', [
    { label: 'Transferable Patterns', value: cl.total_patterns || patterns.length, color: 'var(--cyan)' },
    { label: 'Shared Opportunities', value: cl.total_shared_opportunities || opps.length, color: 'var(--yellow)' },
    { label: 'Reusable Prompts', value: cl.total_reusable_prompts || prompts.length, color: 'var(--blue)' },
    { label: 'Projects Learning', value: Object.keys(insights).length || 3, color: 'var(--green)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  const catColor = { seo: 'var(--green)', ux: 'var(--cyan)', content: 'var(--blue)', monetization: 'var(--yellow)', performance: 'var(--red)' };
  set('crosslearn-patterns', patterns.length ? patterns.map(p => `
    <div style="padding:12px;background:var(--bg2);border-radius:8px;margin-bottom:10px;border-left:3px solid ${catColor[p.category] || 'var(--dim)'}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-weight:700;font-size:13px">${esc(p.pattern_name || '')}</span>
        <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:var(--bg3);color:${catColor[p.category] || 'var(--dim)'}">${(p.category || '').toUpperCase()}</span>
      </div>
      <div style="font-size:11px;color:var(--dim);margin-bottom:6px">
        Learned from: <span style="color:var(--cyan)">${esc(p.learned_from || '')}</span>
        → applies to: <span style="color:var(--green)">${(p.applicable_to || []).join(', ')}</span>
      </div>
      <div style="font-size:12px;margin-bottom:6px">${esc(p.pattern_description || '')}</div>
      <div style="font-size:11px;color:var(--yellow)">Impact: ${esc(p.estimated_impact || '')}</div>
    </div>`).join('') : '<div style="padding:20px;color:var(--dim);text-align:center">Run cross-project learning to identify patterns</div>');

  set('crosslearn-opportunities', opps.length ? opps.map(o => `
    <div style="padding:10px 0;border-bottom:1px solid var(--border)">
      <div style="font-weight:600;font-size:13px;margin-bottom:4px">${esc(o.opportunity || '')}</div>
      <div style="font-size:11px;color:var(--cyan);margin-bottom:2px">${(o.projects || []).join(' + ')}</div>
      <div style="font-size:11px;color:var(--dim)">${esc(o.rationale || '')}</div>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">No shared opportunities identified yet</div>');

  set('crosslearn-insights', Object.entries(insights).length ? Object.entries(insights).map(([proj, insight]) => `
    <div style="padding:10px;background:var(--bg2);border-radius:6px;margin-bottom:8px">
      <div style="font-size:11px;font-weight:700;color:var(--cyan);margin-bottom:4px">${proj.toUpperCase()}</div>
      <div style="font-size:13px">${esc(insight || '')}</div>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">No project-specific insights yet</div>');
}

// ─── Self-Evolution ───────────────────────────────────────────────────────────

function renderEvolution(d) {
  const ev = d.evolution || {};
  const recs = ev.recommended_evolutions || [];
  const thresholds = ev.threshold_recommendations || {};
  const arch = ev.architecture_recommendations || [];
  const tok = ev.token_optimization || {};
  const score = ev.system_maturity_score || 0;

  set('evolution-cards', [
    { label: 'Maturity Score', value: score + '/100', color: score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--yellow)' : 'var(--red)' },
    { label: 'Evolutions Pending', value: recs.filter(r => !r.breaking_change).length, color: 'var(--cyan)' },
    { label: 'Arch Recommendations', value: arch.length, color: 'var(--blue)' },
    { label: 'Token Target', value: '$' + (tok.target_avg_cost_per_feature_usd || 0).toFixed(4), color: 'var(--yellow)' },
  ].map(c => `<div class="card"><div class="card-value" style="color:${c.color}">${c.value}</div><div class="card-label">${c.label}</div></div>`).join(''));

  if (ev.evolution_summary) {
    const el = document.getElementById('evolution-recommendations');
    if (el) el.insertAdjacentHTML('beforebegin', `<div style="padding:12px;background:var(--bg2);border-left:3px solid var(--cyan);border-radius:0 6px 6px 0;margin-bottom:16px;font-size:13px">${esc(ev.evolution_summary)}</div>`);
  }
  if (ev.next_evolution_priority) {
    const el = document.getElementById('evolution-recommendations');
    if (el) el.insertAdjacentHTML('beforebegin', `<div style="padding:10px;background:var(--bg2);border-left:3px solid var(--yellow);border-radius:0 6px 6px 0;margin-bottom:16px;font-size:12px">
      <span style="font-weight:700;color:var(--yellow)">NEXT PRIORITY:</span> ${esc(ev.next_evolution_priority)}
    </div>`);
  }

  const targetColor = { prompt_quality: 'var(--cyan)', qa_thresholds: 'var(--green)', merge_criteria: 'var(--yellow)', token_efficiency: 'var(--blue)', workflow_timing: 'var(--dim)', architecture: 'var(--red)' };
  set('evolution-recommendations', recs.length ? recs.slice(0, 8).map(r => `
    <div style="padding:10px;background:var(--bg2);border-radius:6px;margin-bottom:8px;border-left:3px solid ${targetColor[r.target] || 'var(--dim)'}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:10px;font-weight:700;color:${targetColor[r.target] || 'var(--dim)'}">${(r.target || '').replace(/_/g,' ').toUpperCase()}</span>
        <span style="font-size:11px;color:var(--dim)">priority ${r.priority || 0}</span>
      </div>
      <div style="font-weight:600;font-size:13px;margin-bottom:4px">${esc(r.recommended_change || '')}</div>
      <div style="font-size:11px;color:var(--dim);margin-bottom:4px">Current: ${esc(r.current_state || '')}</div>
      <div style="font-size:11px;color:var(--green)">${esc(r.expected_improvement || '')}</div>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">Run self-evolution engine to generate recommendations</div>');

  set('evolution-thresholds', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      ${[
        {label:'QA Threshold', val: thresholds.qa_threshold, color:'var(--green)'},
        {label:'Trust Threshold', val: thresholds.trust_threshold, color:'var(--cyan)'},
        {label:'Auto-Merge Min', val: thresholds.auto_merge_min_score, color:'var(--yellow)'},
      ].map(t => `
        <div style="background:var(--bg2);padding:12px;border-radius:8px;text-align:center">
          <div style="font-size:22px;font-weight:800;color:${t.color}">${t.val || '–'}</div>
          <div style="font-size:11px;color:var(--dim);margin-top:4px">${t.label}</div>
        </div>`).join('')}
    </div>
    ${thresholds.rationale ? `<div style="margin-top:10px;padding:8px;background:var(--bg2);border-radius:6px;font-size:12px;color:var(--dim)">${esc(thresholds.rationale)}</div>` : ''}`);

  set('evolution-architecture', arch.length ? arch.map(r => `
    <div style="padding:8px 0;border-bottom:1px solid var(--border);display:flex;gap:8px">
      <span style="color:var(--blue)">›</span>
      <span style="font-size:13px">${esc(r)}</span>
    </div>`).join('') : '<div style="padding:16px;color:var(--dim)">No architecture recommendations yet</div>');

  set('evolution-tokens', `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div style="background:var(--bg2);padding:12px;border-radius:8px;text-align:center">
        <div style="font-size:18px;font-weight:700;color:var(--red)">$${(tok.current_avg_cost_per_feature_usd || 0).toFixed(4)}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:4px">Current Avg Cost</div>
      </div>
      <div style="background:var(--bg2);padding:12px;border-radius:8px;text-align:center">
        <div style="font-size:18px;font-weight:700;color:var(--green)">$${(tok.target_avg_cost_per_feature_usd || 0).toFixed(4)}</div>
        <div style="font-size:11px;color:var(--dim);margin-top:4px">Target Avg Cost</div>
      </div>
    </div>
    ${tok.strategy ? `<div style="margin-top:10px;padding:10px;background:var(--bg2);border-radius:6px;font-size:12px">${esc(tok.strategy)}</div>` : ''}`);
}

// ─── Phase G: World Intelligence Render Functions ────────────────────────────

function renderWebIntel(d) {
  const w = d.web_intel || {};
  const opps = w.opportunities || {};
  setCards('webintel-cards', [
    { label: 'Competitor Changes', value: Object.values(w.competitors || {}).flat().reduce((s,c) => s + (c.change_count||0), 0), sub: 'total detected' },
    { label: 'HN Stories', value: (w.hn_stories||[]).length, sub: 'fetched' },
    { label: 'Reddit Posts', value: (w.reddit_posts||[]).length, sub: 'fetched' },
    { label: 'SEO Opps', value: (opps.seo_opportunities||[]).length, sub: 'from web intel' },
  ]);
  const changes = Object.entries(w.competitors||{}).flatMap(([proj,comps]) =>
    comps.filter(c=>c.change_count>0).map(c=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(c.name)}: ${c.change_count} changes</div>`)
  );
  set('webintel-changes', changes.length ? changes.join('') : '<div class="empty-state">No competitor changes detected yet</div>');
  const stories = [...(w.hn_stories||[]).slice(0,5).map(s=>`<div class="list-item"><span class="badge">HN</span> ${esc(s.title)} — ${s.points||0}pts</div>`),
    ...(w.reddit_posts||[]).slice(0,5).map(p=>`<div class="list-item"><span class="badge badge-green">Reddit</span> ${esc(p.title)} — score ${p.score||0}</div>`)];
  set('webintel-trends', stories.length ? stories.join('') : '<div class="empty-state">No trend data yet</div>');
  const seoOpps = (opps.seo_opportunities||[]).map(o=>`<div class="list-item"><span class="badge badge-blue">${esc(o.project||'')}</span> ${esc(o.opportunity||'')} <span style="color:var(--muted);font-size:11px">— ${esc(o.rationale||'')}</span></div>`);
  const contOpps = (opps.content_opportunities||[]).map(o=>`<div class="list-item"><span class="badge badge-green">${esc(o.project||'')}</span> ${esc(o.topic||'')} via ${esc(o.source_trend||'')}</div>`);
  set('webintel-opportunities', [...seoOpps,...contOpps].length ? [...seoOpps,...contOpps].join('') : '<div class="empty-state">Run web intelligence engine to detect opportunities</div>');
}

function renderSeoOpportunities(d) {
  const s = d.seo_opportunities || {};
  const traffic = s.total_addressable_traffic || 0;
  setCards('seoopp-cards', [
    { label: 'Addressable Traffic', value: traffic.toLocaleString(), sub: 'visits/mo' },
    { label: 'Queue Items', value: (s.execution_queue||[]).length, sub: 'ready to execute' },
    { label: 'Injected', value: s.executor_items_injected || 0, sub: 'to executor' },
    { label: 'Projects', value: Object.keys(s.projects||{}).length, sub: 'analyzed' },
  ]);
  const clusters = Object.entries(s.projects||{}).flatMap(([proj,pd]) =>
    (pd.topical_clusters||[]).map(c=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(c.hub_keyword||'')} <span class="badge ${c.difficulty==='easy'?'badge-green':c.difficulty==='medium'?'badge-yellow':'badge-red'}">${esc(c.difficulty||'')}</span> <span style="color:var(--muted);font-size:11px">${(c.est_monthly_searches||0).toLocaleString()}/mo</span></div>`)
  );
  set('seoopp-clusters', clusters.length ? clusters.join('') : '<div class="empty-state">Run SEO opportunity engine to generate clusters</div>');
  const qw = Object.entries(s.projects||{}).flatMap(([proj,pd]) =>
    (pd.quick_wins||[]).map(w=>`<div class="list-item"><span class="badge badge-green">${proj}</span> ${esc(w.keyword||'')} — +${(w.est_traffic_gain||0).toLocaleString()} visits</div>`)
  );
  set('seoopp-quickwins', qw.length ? qw.join('') : '<div class="empty-state">No quick wins yet</div>');
  const queue = (s.execution_queue||[]).slice(0,10).map(q=>`<div class="list-item"><span class="badge badge-blue">${esc(q.project||'')}</span> ${esc(q.title||'')} <span style="color:var(--muted);font-size:11px">score: ${(q.priority_score||0).toFixed(1)}</span></div>`);
  set('seoopp-queue', queue.length ? queue.join('') : '<div class="empty-state">Queue empty</div>');
}

function renderCompetitorMemory(d) {
  const c = d.competitor_memory || {};
  setCards('compmem-cards', [
    { label: 'Competitors Tracked', value: c.total_competitors || 0, sub: 'total' },
    { label: 'Reachable', value: c.reachable_competitors || 0, sub: 'successfully profiled' },
    { label: 'Projects', value: Object.keys(c.projects||{}).length, sub: 'monitored' },
  ]);
  const profiles = Object.entries(c.projects||{}).flatMap(([proj,pd]) =>
    (pd.profiles||[]).map(p=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> <strong>${esc(p.name||'')}</strong> ${p.reachable?'<span class="badge badge-green">online</span>':'<span class="badge badge-red">offline</span>'} <span style="color:var(--muted);font-size:11px">${esc((p.seo||{}).title||'')}</span></div>`)
  );
  set('compmem-profiles', profiles.length ? profiles.join('') : '<div class="empty-state">Run competitor memory system to profile competitors</div>');
  const patterns = Object.entries(c.projects||{}).flatMap(([proj,pd]) => {
    const p = pd.patterns||{};
    return [...(p.layout_patterns||[]).map(x=>`<div class="list-item"><span class="badge">Layout</span> ${esc(x.pattern||'')} — ${esc(x.transfer_recommendation||'')}</div>`),
      ...(p.monetization_patterns||[]).map(x=>`<div class="list-item"><span class="badge badge-green">Monetize</span> ${esc(x.pattern||'')} — ${esc(x.est_revenue_impact||'')}</div>`)];
  });
  set('compmem-patterns', patterns.length ? patterns.join('') : '<div class="empty-state">No patterns extracted yet</div>');
  const recs = Object.entries(c.all_recommendations||{}).flatMap(([proj,rs]) =>
    (rs||[]).map(r=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(r)}</div>`)
  );
  set('compmem-recs', recs.length ? recs.join('') : '<div class="empty-state">No recommendations yet</div>');
}

function renderSocialSignals(d) {
  const s = d.social_signals || {};
  const totalPosts = s.total_posts_analyzed || 0;
  setCards('social-cards', [
    { label: 'Posts Analyzed', value: totalPosts.toLocaleString(), sub: 'total' },
    { label: 'Projects', value: Object.keys(s.projects||{}).length, sub: 'monitored' },
    { label: 'Cross-Project Trends', value: (s.cross_project?.cross_project_trends||[]).length, sub: 'detected' },
  ]);
  const viral = Object.entries(s.projects||{}).flatMap(([proj,pd]) => {
    const sa = pd.sentiment_analysis||{};
    return (sa.viral_topics||[]).map(t=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(t.topic||'')} <span class="badge ${t.momentum==='rising'?'badge-green':t.momentum==='declining'?'badge-red':'badge-yellow'}">${esc(t.momentum||'')}</span></div>`);
  });
  set('social-viral', viral.length ? viral.join('') : '<div class="empty-state">Run social signal engine to detect viral topics</div>');
  const contOpps = Object.entries(s.projects||{}).flatMap(([proj,pd]) => {
    const sa = pd.sentiment_analysis||{};
    return (sa.content_opportunities||[]).map(o=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(o.title||'')} <span class="badge badge-green">${esc(o.format||'')}</span></div>`);
  });
  set('social-opportunities', contOpps.length ? contOpps.join('') : '<div class="empty-state">No content opportunities yet</div>');
  const kws = Object.entries(s.projects||{}).flatMap(([proj,pd]) =>
    (pd.trending_keywords||[]).slice(0,5).map(k=>`<span style="display:inline-block;margin:3px;padding:3px 8px;background:var(--bg2);border-radius:4px;font-size:12px">${esc(k.word||'')} <span style="color:var(--muted)">(${k.count||0})</span></span>`)
  );
  set('social-keywords', kws.length ? `<div style="padding:12px">${kws.join('')}</div>` : '<div class="empty-state">No keywords yet</div>');
}

function renderTrafficIntel(d) {
  const t = d.traffic_intel || {};
  const total6mo = t.total_addressable_6mo || 0;
  setCards('traffic-cards', [
    { label: '6mo Addressable', value: total6mo.toLocaleString(), sub: 'visits with SEO' },
    { label: 'Projects', value: Object.keys(t.projects||{}).length, sub: 'analyzed' },
  ]);
  const gaps = Object.entries(t.projects||{}).flatMap(([proj,pd]) =>
    (pd.traffic_gaps||[]).map(g=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> vs ${esc(g.competitor||'')} — gap: ${(g.gap_visits||0).toLocaleString()} visits (${g.gap_pct||0}%)</div>`)
  );
  set('traffic-gaps', gaps.length ? gaps.join('') : '<div class="empty-state">Run traffic intelligence engine</div>');
  const ctr = Object.entries(t.projects||{}).flatMap(([proj,pd]) =>
    (pd.ctr_opportunities||[]).slice(0,3).map(k=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(k.keyword||'')} — pos #${k.est_serp_position} CTR ${k.est_ctr}% → ${(k.est_monthly_clicks||0).toLocaleString()} clicks/mo</div>`)
  );
  set('traffic-ctr', ctr.length ? ctr.join('') : '<div class="empty-state">No CTR data yet</div>');
  const seasonal = Object.entries(t.projects||{}).map(([proj,pd]) => {
    const se = pd.seasonal||{};
    return `<div class="list-item"><span class="badge badge-blue">${proj}</span> ${se.trend||'stable'} — current ×${se.current_multiplier||1} | peak: month ${se.peak_month||'?'} ×${se.peak_multiplier||1} ${se.is_peak_season?'<span class="badge badge-green">PEAK NOW</span>':''}</div>`;
  });
  set('traffic-seasonal', seasonal.length ? seasonal.join('') : '<div class="empty-state">No seasonal data</div>');
}

function renderMonetization(d) {
  const m = d.monetization || {};
  const monthlyLift = m.portfolio_monthly_lift_usd || 0;
  const annualLift = m.portfolio_annual_lift_usd || 0;
  setCards('monetize-cards', [
    { label: 'Monthly Lift', value: `$${monthlyLift.toLocaleString()}`, sub: 'est. revenue gain' },
    { label: 'Annual Lift', value: `$${annualLift.toLocaleString()}`, sub: 'projected' },
    { label: 'Projects', value: Object.keys(m.projects||{}).length, sub: 'optimized' },
  ]);
  const gaps = Object.entries(m.projects||{}).flatMap(([proj,pd]) =>
    (pd.gaps_detected||[]).map(g=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> <span class="badge ${g.severity==='critical'?'badge-red':g.severity==='high'?'badge-red':'badge-yellow'}">${esc(g.severity||'')}</span> ${esc(g.action||'')} ${g.est_monthly_lift_usd?`<span style="color:var(--muted);font-size:11px">+$${g.est_monthly_lift_usd}/mo</span>`:''}</div>`)
  );
  set('monetize-gaps', gaps.length ? gaps.join('') : '<div class="empty-state">Run monetization engine to detect gaps</div>');
  const qw = Object.entries(m.projects||{}).flatMap(([proj,pd]) =>
    ((pd.monetization_plan||{}).quick_wins||[]).map(q=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(q.action||'')} — ${esc(q.effort||'')} effort → +$${(q.est_monthly_lift_usd||0).toLocaleString()}/mo</div>`)
  );
  set('monetize-quickwins', qw.length ? qw.join('') : '<div class="empty-state">No quick wins yet</div>');
  const streams = Object.entries(m.projects||{}).flatMap(([proj,pd]) =>
    ((pd.monetization_plan||{}).new_revenue_streams||[]).map(s=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> ${esc(s.stream||'')} — $${(s.est_monthly_usd||0).toLocaleString()}/mo</div>`)
  );
  set('monetize-streams', streams.length ? streams.join('') : '<div class="empty-state">No new streams identified yet</div>');
}

function renderCampaigns(d) {
  const c = d.campaigns || {};
  setCards('campaigns-cards', [
    { label: 'Pages Generated', value: c.total_pages_generated || 0, sub: 'landing pages' },
    { label: 'Injected', value: c.executor_items_injected || 0, sub: 'to executor' },
    { label: 'Projects', value: Object.keys(c.projects||{}).length, sub: 'campaigns' },
  ]);
  const active = Object.entries(c.projects||{}).flatMap(([proj,pd]) =>
    (pd.campaigns||[]).map(camp=>`<div class="list-item"><span class="badge badge-blue">${proj}</span> <strong>${esc(camp.hub_keyword||'')}</strong> → <code>${esc(camp.hub_path||'')}</code> <span class="badge ${camp.difficulty==='easy'?'badge-green':camp.difficulty==='medium'?'badge-yellow':'badge-red'}">${esc(camp.difficulty||'')}</span> ${(camp.est_monthly_searches||0).toLocaleString()} searches/mo</div>`)
  );
  set('campaigns-active', active.length ? active.join('') : '<div class="empty-state">Run campaign engine to generate landing pages</div>');
  const seq = Object.values(c.projects||{}).flatMap(pd =>
    (pd.launch_sequence||[]).slice(0,5).map(s=>`<div class="list-item">Week ${s.week}: <strong>${esc(s.action||'')}</strong> — ${esc(s.title||s.content||s.anchor||'')}</div>`)
  );
  set('campaigns-sequence', seq.length ? seq.join('') : '<div class="empty-state">No launch sequence yet</div>');
}

function renderRealtimeAlerts(d) {
  const r = d.realtime_alerts || {};
  const level = r.alert_level || 'normal';
  const levelColor = { critical: 'badge-red', high: 'badge-red', elevated: 'badge-yellow', normal: 'badge-green' }[level] || 'badge-green';
  setCards('realtime-cards', [
    { label: 'Alert Level', value: level.toUpperCase(), sub: 'current status' },
    { label: 'Posts Scanned', value: (r.posts_scanned||0).toLocaleString(), sub: 'this cycle' },
    { label: 'Events Detected', value: r.events_detected || 0, sub: 'high-impact' },
    { label: 'Emergency Injected', value: r.executor_items_injected || 0, sub: 'to queue' },
  ]);
  const analysis = r.analysis || {};
  const alerts = (r.events||[]).slice(0,8).map(e=>`<div class="list-item"><span class="badge ${e.impact_score>=8?'badge-red':'badge-yellow'}">${e.impact_score||0}</span> ${esc(e.title||'')} <span style="color:var(--muted);font-size:11px">${(e.event_types||[]).join(', ')}</span></div>`);
  set('realtime-alerts', alerts.length ? alerts.join('') : '<div class="empty-state">No high-impact events detected</div>');
  const actions = (analysis.urgent_actions||[]).map(a=>`<div class="list-item"><span class="badge badge-blue">${esc(a.project||'')}</span> ${esc(a.action||'')} <span style="color:var(--muted);font-size:11px">deadline: ${a.deadline_hours||24}h</span></div>`);
  set('realtime-actions', actions.length ? actions.join('') : '<div class="empty-state">No urgent actions</div>');
  const contOpps = (analysis.content_opportunities||[]).map(o=>`<div class="list-item"><span class="badge badge-blue">${esc(o.project||'')}</span> ${esc(o.topic||'')} — ${esc(o.format||'')} | ${esc(o.urgency||'')}</div>`);
  set('realtime-content', contOpps.length ? contOpps.join('') : '<div class="empty-state">No content opportunities from events</div>');
}

function renderKnowledgeGraph(d) {
  const kg = d.knowledge_graph || {};
  const metrics = kg.metrics || {};
  const insights = kg.insights || {};
  setCards('kgraph-cards', [
    { label: 'Total Nodes', value: metrics.total_nodes || 0, sub: 'entities' },
    { label: 'Total Edges', value: metrics.total_edges || 0, sub: 'relationships' },
    { label: 'Density', value: metrics.density || 0, sub: 'graph density' },
    { label: 'Connections', value: (insights.hidden_connections||[]).length, sub: 'hidden found' },
  ]);
  const connections = (insights.hidden_connections||[]).map(c=>`<div class="list-item"><strong>${esc(c.connection||'')}</strong> <span style="color:var(--muted);font-size:11px">— ${esc(c.strategic_value||'')}</span></div>`);
  set('kgraph-connections', connections.length ? connections.join('') : '<div class="empty-state">Run knowledge graph engine to discover connections</div>');
  const crossOpps = (insights.cross_project_opportunities||[]).map(o=>`<div class="list-item"><span class="badge badge-blue">${esc(o.from_project||'')}</span> → <span class="badge badge-green">${esc(o.to_project||'')}</span> ${esc(o.opportunity||'')} via ${esc(o.mechanism||'')}</div>`);
  set('kgraph-crossopp', crossOpps.length ? crossOpps.join('') : '<div class="empty-state">No cross-project opportunities detected</div>');
  const topNodes = (metrics.top_connected_nodes||[]).map(n=>`<div class="list-item"><code>${esc(n.id||'')}</code> — degree: ${n.degree||0}</div>`);
  set('kgraph-nodes', topNodes.length ? topNodes.join('') : '<div class="empty-state">No node data</div>');
  const clusters = (insights.strategic_clusters||[]).map(c=>`<div class="list-item"><strong>${esc(c.cluster_name||'')}</strong> — ${esc(c.theme||'')} (${(c.nodes||[]).length} nodes)</div>`);
  set('kgraph-clusters', clusters.length ? clusters.join('') : '<div class="empty-state">No clusters identified</div>');
}

// ─── Phase H: Agentic OS Render Functions ────────────────────────────────────

function renderAgents(d) {
  const k = d.kernel || {};
  const agentStates = k.agent_states || {};
  const swarm = k.swarm_activity || {};
  const evo = d.agent_evolution || {};
  const evoResults = evo.evolution_results || {};
  const hierarchy = evo.hierarchy || {};

  setCards('agents-cards', [
    { label: 'Active Agents', value: swarm.active_agents || Object.keys(agentStates).length, sub: `of ${swarm.total_agents || 8} total` },
    { label: 'Avg Performance', value: `${(swarm.avg_agent_performance || 0).toFixed(1)}/100`, sub: 'composite score' },
    { label: 'Swarm Health', value: (swarm.swarm_health || 'unknown').toUpperCase(), sub: 'overall state' },
    { label: 'Evolution Cycles', value: swarm.evolution_cycles || 0, sub: 'completed' },
  ]);

  // Hierarchy
  const tier1 = (hierarchy.tier_1 || ['orchestrator']).join(', ');
  const tier2 = (hierarchy.tier_2 || []).join(', ');
  const tier3 = (hierarchy.tier_3 || []).join(', ');
  const standouts = (hierarchy.standout_agents || []).join(', ');
  set('agents-hierarchy', `
    <div style="padding:16px;font-family:monospace">
      <div style="text-align:center;color:var(--accent);font-weight:700;margin-bottom:8px">Tier 1: ${esc(tier1)}</div>
      <div style="text-align:center;font-size:20px;margin:4px 0">↓</div>
      <div style="text-align:center;color:#10b981;font-weight:600;margin-bottom:8px">Tier 2: ${esc(tier2 || 'seo, analytics')}</div>
      <div style="text-align:center;font-size:20px;margin:4px 0">↓</div>
      <div style="text-align:center;color:var(--muted);margin-bottom:12px">Tier 3: ${esc(tier3 || 'executor, reviewer, optimizer, monetizer')}</div>
      ${standouts ? `<div style="text-align:center;font-size:11px;color:#f59e0b">⭐ Standouts: ${esc(standouts)}</div>` : ''}
      <div style="text-align:center;font-size:11px;color:var(--muted);margin-top:8px">Hierarchy health: ${hierarchy.hierarchy_health_score || 70}/100</div>
    </div>`);

  // Performance
  const perfItems = Object.entries(agentStates).map(([id, a]) => {
    const er = evoResults[id] || {};
    const score = er.performance_score || a.performance_score || 50;
    const conf = (er.new_confidence || a.confidence || 0.75) * 100;
    const bar = `<div style="height:4px;background:var(--bg2);border-radius:2px;margin-top:4px"><div style="height:4px;background:${score>=70?'#10b981':score>=50?'#f59e0b':'#ef4444'};width:${score}%;border-radius:2px"></div></div>`;
    return `<div class="list-item"><strong>${esc(a.name||id)}</strong> <span class="badge badge-blue">${esc(a.role||id)}</span> score: ${score}/100 | conf: ${conf.toFixed(0)}% ${bar}</div>`;
  });
  set('agents-performance', perfItems.length ? perfItems.join('') : '<div class="empty-state">Run agent evolution to see performance</div>');

  // Skills
  const skillItems = Object.entries(agentStates).map(([id, a]) => {
    const skills = a.skills || {};
    const topSkills = Object.entries(skills).sort((x,y)=>y[1]-x[1]).slice(0,3)
      .map(([sk, v]) => `<span style="margin:2px;padding:2px 6px;background:var(--bg2);border-radius:3px;font-size:11px">${esc(sk)}: ${(v*100).toFixed(0)}%</span>`).join('');
    return `<div class="list-item"><span class="badge badge-blue">${esc(id)}</span> ${topSkills || '<span style="color:var(--muted)">no skills data</span>'}</div>`;
  });
  set('agents-skills', skillItems.length ? skillItems.join('') : '<div class="empty-state">Run agent bus to initialize agents</div>');
}

function renderCognition(d) {
  const cog = d.cognition || {};
  setCards('cognition-cards', [
    { label: 'Cognition Cycle', value: `#${cog.cognition_cycle || 0}`, sub: 'lifetime' },
    { label: 'Health Score', value: `${cog.health_score || 0}/100`, sub: 'overall cognition' },
    { label: 'Chain Confidence', value: `${((cog.chain_confidence || 0) * 100).toFixed(0)}%`, sub: 'reasoning quality' },
    { label: 'Reasoning Steps', value: cog.reasoning_steps || 0, sub: 'in latest chain' },
  ]);

  const chain = cog.latest_chain || {};
  const steps = (chain.reasoning_steps || []).map(s =>
    `<div class="list-item"><span class="badge badge-blue">Step ${s.step}</span> <strong>${esc(s.action||'')}</strong> → ${esc(s.expected_outcome||'')} <span style="color:var(--muted);font-size:11px">${s.timeline_weeks}w | ${((s.confidence||0)*100).toFixed(0)}%</span></div>`
  );
  set('cognition-chain', steps.length ? steps.join('') : '<div class="empty-state">Run cognition engine to build reasoning chain</div>');

  const reflection = cog.reflection || {};
  const dims = Object.entries(reflection.dimension_scores || {}).map(([k,v]) =>
    `<div class="list-item" style="display:flex;justify-content:space-between"><span>${esc(k.replace(/_/g,' '))}</span><span style="color:${v>=70?'#10b981':v>=50?'#f59e0b':'#ef4444'}">${v}/100</span></div>`
  );
  const reflItems = [
    ...(reflection.what_is_working || []).map(w => `<div class="list-item"><span style="color:#10b981">✓</span> ${esc(w)}</div>`),
    ...(reflection.what_is_not_working || []).map(w => `<div class="list-item"><span style="color:#ef4444">✗</span> ${esc(w)}</div>`),
  ];
  set('cognition-reflection', [...dims, ...reflItems].length ? [...dims, ...reflItems].join('') : '<div class="empty-state">No reflection data</div>');

  const plan = cog.long_horizon_plan || {};
  const quarters = (plan.quarters || []).map(q =>
    `<div class="list-item"><strong>${esc(q.quarter||'')}</strong>: ${esc(q.theme||'')} — ${(q.primary_objectives||[]).join(', ')}</div>`
  );
  set('cognition-horizon', quarters.length ? quarters.join('') : '<div class="empty-state">Run cognition engine (every 5 cycles) to generate 12-month plan</div>');

  const objs = (cog.active_objectives || []).map((o,i) =>
    `<div class="list-item"><span class="badge badge-blue">${i+1}</span> ${esc(o)}</div>`
  );
  set('cognition-objectives', objs.length ? objs.join('') : '<div class="empty-state">No objectives set</div>');
}

function renderGovernance(d) {
  const gov = d.governance || {};
  const aiReview = gov.ai_review || {};
  const riskColor = { critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#10b981' };
  setCards('governance-cards', [
    { label: 'Company Mode', value: (gov.mode || 'semi_autonomous').replace(/_/g,' ').toUpperCase(), sub: gov.mode_config?.description || '' },
    { label: 'Approved', value: gov.approved || 0, sub: 'actions cleared' },
    { label: 'Blocked', value: gov.blocked || 0, sub: 'actions stopped' },
    { label: 'Portfolio Risk', value: `${aiReview.portfolio_risk_score || 30}/100`, sub: 'governance score' },
  ]);

  const approved = (gov.approved_actions || []).slice(0,8).map(a =>
    `<div class="list-item"><span class="badge badge-green">✓</span> <span class="badge badge-blue">${esc(a.project||'')}</span> ${esc(a.title||'')} <span style="color:var(--muted);font-size:11px">risk: ${a.governance?.risk_assessment?.risk_score||0}</span></div>`
  );
  set('governance-approved', approved.length ? approved.join('') : '<div class="empty-state">No approved actions yet</div>');

  const blocked = (gov.blocked_actions || []).slice(0,8).map(a =>
    `<div class="list-item"><span class="badge badge-red">✗</span> <span class="badge badge-blue">${esc(a.project||'')}</span> ${esc(a.title||'')} <span style="color:#ef4444;font-size:11px">${esc(a.governance?.reason||'')}</span></div>`
  );
  set('governance-blocked', blocked.length ? blocked.join('') : '<div class="empty-state">No blocked actions</div>');

  const flags = (aiReview.risk_flags || []).map(f =>
    `<div class="list-item"><span style="color:${riskColor[f.severity]||'#f59e0b'}">[${esc(f.severity||'')}]</span> ${esc(f.flag||'')}</div>`
  );
  const recs = (aiReview.recommendations || []).map(r =>
    `<div class="list-item"><span class="badge badge-blue">rec</span> ${esc(r)}</div>`
  );
  set('governance-risks', [...flags, ...recs].length ? [...flags, ...recs].join('') : '<div class="empty-state">No risk flags — governance healthy</div>');
}

function renderEconomy(d) {
  const econ = d.task_economy || {};
  const portfolio = econ.portfolio || {};
  const ai = econ.ai_analysis || {};
  const healthColor = { excellent: '#10b981', good: '#3b82f6', fair: '#f59e0b', poor: '#ef4444' };

  setCards('economy-cards', [
    { label: 'Tasks Scored', value: econ.tasks_scored || 0, sub: 'this cycle' },
    { label: 'Selected', value: portfolio.total_tasks || 0, sub: `$${(portfolio.budget_used_usd||0).toFixed(4)} used` },
    { label: 'Est. Annual Value', value: `$${(portfolio.total_est_annual_value_usd||0).toLocaleString()}`, sub: 'portfolio ROI' },
    { label: 'Economy Health', value: (ai.economy_health||'good').toUpperCase(), sub: `score: ${ai.economy_score||0}/100` },
  ]);

  const tasks = (econ.top_tasks || []).slice(0,10).map(t =>
    `<div class="list-item"><span style="color:#f59e0b;font-weight:700;min-width:40px;display:inline-block">${(t.economy_score||0).toFixed(1)}</span> <span class="badge badge-blue">${esc(t.project||'')}</span> ${esc(t.title||'')} <span style="color:var(--muted);font-size:11px">ROI ${(t.roi_model?.roi_ratio||0).toLocaleString()}× | $${(t.roi_model?.total_value_annual_usd||0).toFixed(0)}/yr</span></div>`
  );
  set('economy-tasks', tasks.length ? tasks.join('') : '<div class="empty-state">Run task economy engine to score tasks</div>');

  const byProj = Object.entries(econ.by_project || {}).map(([proj, data]) =>
    `<div class="list-item"><span class="badge badge-blue">${esc(proj)}</span> ${data.count} tasks | $${(data.total_annual_value_usd||0).toFixed(0)}/yr | $${(data.total_cost_usd||0).toFixed(4)} cost</div>`
  );
  set('economy-portfolio', byProj.length ? byProj.join('') : '<div class="empty-state">No portfolio data</div>');

  const insights = (ai.economy_insights || []).map(i => `<div class="list-item">${esc(i)}</div>`);
  const reallocSugs = (ai.reallocation_suggestions || []).map(s =>
    `<div class="list-item"><span class="badge badge-yellow">realloc</span> ${esc(s.from||'')} → ${esc(s.to||'')} — ${esc(s.rationale||'')}</div>`
  );
  set('economy-insights', [...insights, ...reallocSugs].length ? [...insights, ...reallocSugs].join('') :
    `<div style="padding:12px;color:var(--muted)">${esc(ai.budget_efficiency||'No insights yet')}</div>`);
}

function renderKernel(d) {
  const k = d.kernel || {};
  const swarm = k.swarm_activity || {};
  const tokenFlow = k.token_flow || {};
  const memFlow = k.memory_flow || {};
  const ai = k.ai_analysis || {};
  const statusColor = { nominal:'#10b981', excellent:'#3b82f6', degraded:'#f59e0b', critical:'#ef4444' };

  setCards('kernel-cards', [
    { label: 'Ops Status', value: (k.operational_status||'nominal').toUpperCase(), sub: `score: ${k.ops_score||0}/100` },
    { label: 'Memory', value: `${(memFlow.total_size_kb||0).toFixed(0)} KB`, sub: `${memFlow.total_memory_files||0} files` },
    { label: 'Token Flow', value: `${(tokenFlow.est_tokens_per_day||0).toLocaleString()}/day`, sub: `$${(tokenFlow.est_cost_per_day_usd||0).toFixed(4)}/day` },
    { label: 'Intel Sources', value: k.intelligence_sources_loaded || 0, sub: 'loaded this cycle' },
  ]);

  const bottlenecks = (k.bottlenecks || []).map(b => {
    const sev = { high:'badge-red', medium:'badge-yellow', low:'badge-green' }[b.severity] || 'badge-yellow';
    return `<div class="list-item"><span class="badge ${sev}">${esc(b.severity||'')}</span> <strong>${esc(b.component||'')}</strong> — ${esc(b.description||'')}</div>`;
  });
  set('kernel-bottlenecks', bottlenecks.length ? bottlenecks.join('') : '<div class="empty-state" style="color:#10b981">No bottlenecks detected — system flowing smoothly</div>');

  const swarmItems = [
    `<div class="list-item">Active agents: <strong>${swarm.active_agents||0}/${swarm.total_agents||8}</strong></div>`,
    `<div class="list-item">Active tasks: <strong>${swarm.active_tasks||0}</strong></div>`,
    `<div class="list-item">Tasks dispatched: <strong>${swarm.tasks_dispatched_cycle||0}</strong> this cycle</div>`,
    `<div class="list-item">Avg performance: <strong>${(swarm.avg_agent_performance||0).toFixed(1)}/100</strong></div>`,
    `<div class="list-item">Evolution cycles: <strong>${swarm.evolution_cycles||0}</strong></div>`,
  ];
  set('kernel-swarm', swarmItems.join(''));

  const flowItems = [
    `<div class="list-item">Total tokens all-time: <strong>${(tokenFlow.total_tokens_all_time||0).toLocaleString()}</strong></div>`,
    `<div class="list-item">Total cost all-time: <strong>$${(tokenFlow.total_cost_all_time_usd||0).toFixed(4)}</strong></div>`,
    `<div class="list-item">Est. per day: <strong>${(tokenFlow.est_tokens_per_day||0).toLocaleString()} tokens / $${(tokenFlow.est_cost_per_day_usd||0).toFixed(4)}</strong></div>`,
  ];
  set('kernel-tokenflow', flowItems.join(''));

  const insights = [
    ...(ai.immediate_actions||[]).map(a => `<div class="list-item"><span class="badge badge-red">now</span> ${esc(a)}</div>`),
    ...(ai.optimization_opportunities||[]).map(o => `<div class="list-item"><span class="badge badge-green">optimize</span> ${esc(o)}</div>`),
  ];
  const insight = ai.kernel_insight ? `<div style="padding:12px;background:var(--bg2);border-radius:6px;font-size:12px;margin-top:8px">${esc(ai.kernel_insight)}</div>` : '';
  set('kernel-insights', insights.length ? insights.join('') + insight : `<div class="empty-state">Run operations kernel for insights</div>${insight}`);
}

function renderCivilization(d) {
  const k = d.kernel || {};
  const modeInfo = k.mode_info || {};
  const ai = k.ai_analysis || {};
  const execGraph = k.execution_graph || {};
  const modeColors = { assisted:'#6b7280', semi_autonomous:'#3b82f6', autonomous:'#10b981', civilization:'#8b5cf6' };
  const mode = k.company_mode || 'semi_autonomous';
  const modeColor = modeColors[mode] || '#3b82f6';

  setCards('civilization-cards', [
    { label: 'Company Mode', value: (modeInfo.label||mode).toUpperCase(), sub: `Autonomy level ${modeInfo.autonomy||1}/4` },
    { label: 'Exec Graph Nodes', value: execGraph.node_count || 0, sub: `${execGraph.edge_count||0} edges` },
    { label: 'Mode Recommendation', value: (ai.mode_recommendation||mode).replace(/_/g,' '), sub: 'AI suggested' },
    { label: 'Company Velocity', value: 'VIEW BELOW', sub: 'see description' },
  ]);

  set('civilization-mode', `
    <div style="padding:20px;text-align:center">
      <div style="font-size:2rem;font-weight:900;color:${modeColor};margin-bottom:8px">${esc(modeInfo.label||mode)}</div>
      <div style="color:var(--muted);margin-bottom:16px">Autonomy Level ${modeInfo.autonomy||1}/4</div>
      <div style="padding:12px;background:var(--bg2);border-radius:8px;font-size:13px">${esc(ai.company_velocity||'Standard autonomous execution')}</div>
      ${ai.mode_recommendation && ai.mode_recommendation !== mode ?
        `<div style="margin-top:12px;padding:8px;background:#1e1b4b;border-radius:6px;font-size:11px;color:#a78bfa">AI recommends switching to: <strong>${esc(ai.mode_recommendation)}</strong></div>` : ''}
    </div>`);

  const nodes = (execGraph.nodes || []).slice(0,12).map(n =>
    `<span style="display:inline-block;margin:3px;padding:3px 8px;background:${n.type==='agent'?'#1e3a5f':'var(--bg2)'};border-radius:4px;font-size:11px;color:${n.type==='agent'?'#60a5fa':'var(--fg)'}">${esc(n.label||n.id||'')}</span>`
  );
  set('civilization-graph', nodes.length ? `<div style="padding:12px">${nodes.join('')}</div>` : '<div class="empty-state">Graph building — run operations kernel</div>');

  const actions = (ai.immediate_actions||[]).map(a =>
    `<div class="list-item"><span class="badge badge-red">urgent</span> ${esc(a)}</div>`
  );
  set('civilization-actions', actions.length ? actions.join('') : '<div class="empty-state" style="color:#10b981">No immediate actions required</div>');

  const predictions = (ai.predicted_issues||[]).map(p =>
    `<div class="list-item"><span class="badge badge-yellow">${esc(p.timeline||'?')}</span> ${esc(p.issue||'')} <span style="color:var(--muted);font-size:11px">(${((p.probability||0)*100).toFixed(0)}% probability)</span></div>`
  );
  set('civilization-predictions', predictions.length ? predictions.join('') : '<div class="empty-state" style="color:#10b981">No issues predicted</div>');
}

// ─── Phase J: Infrastructure ─────────────────────────────────────────────────

function renderDeployments(d) {
  const dep = d.deployment_pipeline || {};
  const health = dep.overall_health || 0;
  const status = dep.deployment_status || 'unknown';
  const projects = dep.projects || {};
  const ai = dep.ai_analysis || {};
  const statusColor = status === 'healthy' ? 'green' : status === 'degraded' ? 'yellow' : 'red';

  set('deployments-cards', `
    <div class="card"><div class="card-label">Overall Health</div><div class="card-value" style="color:var(--${statusColor})">${health}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Status</div><div class="card-value" style="color:var(--${statusColor})">${esc(status.toUpperCase())}</div></div>
    <div class="card"><div class="card-label">Projects Monitored</div><div class="card-value">${Object.keys(projects).length}</div></div>
    <div class="card"><div class="card-label">Rollbacks Needed</div><div class="card-value" style="color:var(--${Object.values(projects).some(p=>p.rollback_recommended)?'red':'green'})">${Object.values(projects).filter(p=>p.rollback_recommended).length}</div></div>
  `);

  const healthRows = Object.entries(projects).map(([pid, p]) => {
    const hc = p.health_score >= 70 ? 'green' : p.health_score >= 40 ? 'yellow' : 'red';
    const avail = p.availability || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — <span style="color:var(--${hc})">${p.health_score}/100</span> [${esc(p.health_status||'')}]</div>
      <div class="activity-meta">${p.domain} · ${avail.available ? `✓ ${avail.latency_ms}ms` : '✗ unavailable'}</div>
    </div></div>`;
  }).join('');
  set('deployments-health', healthRows || '<div class="empty-state">No deployment data yet — workflow not yet run</div>');

  const cwvRows = Object.entries(projects).map(([pid, p]) => {
    const cwv = p.cwv || {};
    if (!cwv.performance && !cwv.lcp_ms) return `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(pid)}</div><div class="activity-meta">CWV data unavailable</div></div></div>`;
    const lcpColor = (cwv.lcp_ms||0) < 2500 ? 'green' : (cwv.lcp_ms||0) < 4000 ? 'yellow' : 'red';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — Perf ${cwv.performance||0} · SEO ${cwv.seo||0} · Access ${cwv.accessibility||0}</div>
      <div class="activity-meta">LCP <span style="color:var(--${lcpColor})">${cwv.lcp_ms||0}ms</span> · CLS ${cwv.cls||0} · TTFB ${cwv.ttfb_ms||0}ms</div>
    </div></div>`;
  }).join('');
  set('deployments-cwv', cwvRows || '<div class="empty-state">No CWV data yet</div>');

  const rbRows = Object.entries(projects).flatMap(([pid, p]) =>
    (p.rollback_triggers || []).length > 0
      ? [{ pid, triggers: p.rollback_triggers }]
      : []
  ).map(({ pid, triggers }) =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--red)">${esc(pid)} — ROLLBACK RECOMMENDED</div>
      ${triggers.map(t => `<div class="activity-meta">• ${esc(t)}</div>`).join('')}
    </div></div>`
  ).join('');
  set('deployments-rollback', rbRows || '<div class="empty-state" style="color:var(--green)">No rollback triggers — all deployments healthy</div>');

  const recRows = (ai.recommendations || []).map(r =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-meta">${esc(r)}</div></div></div>`
  ).join('');
  set('deployments-recs', (ai.summary ? `<div class="activity-item"><div class="activity-body"><div class="activity-meta">${esc(ai.summary)}</div></div></div>` : '') + recRows || '<div class="empty-state">No recommendations yet</div>');
}

function renderVecMem(d) {
  const vm = d.vector_memory || {};
  const total = vm.total_memories || 0;
  const embedded = vm.embedded_memories || 0;
  const byType = vm.by_type || {};
  const embRate = total > 0 ? Math.round(embedded / total * 100) : 0;

  set('vecmem-cards', `
    <div class="card"><div class="card-label">Total Memories</div><div class="card-value" style="color:var(--blue)">${total}</div></div>
    <div class="card"><div class="card-label">Embedded</div><div class="card-value" style="color:var(--green)">${embedded}</div></div>
    <div class="card"><div class="card-label">Embedding Rate</div><div class="card-value" style="color:var(--${embRate>=70?'green':embRate>=30?'yellow':'muted'})">${embRate}%</div></div>
    <div class="card"><div class="card-label">Memory Types</div><div class="card-value">${Object.keys(byType).length}</div></div>
  `);

  const typeRows = Object.entries(byType).sort((a,b)=>b[1]-a[1]).map(([type, count]) =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(type.replace(/_/g,' '))}</div>
      <div class="activity-meta">${count} memories</div>
    </div></div>`
  ).join('');
  set('vecmem-types', typeRows || '<div class="empty-state">No memories indexed yet</div>');

  set('vecmem-index', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Embedding Model</div>
      <div class="activity-meta">${esc(vm.embedding_model || 'text-embedding-3-small')}</div>
    </div></div>
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Embeddings Enabled</div>
      <div class="activity-meta" style="color:var(--${vm.embeddings_enabled?'green':'yellow'})">${vm.embeddings_enabled ? 'Yes — OpenAI active' : 'No — keyword fallback mode'}</div>
    </div></div>
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">New Added This Cycle</div>
      <div class="activity-meta">${vm.new_memories_added || 0} · ${vm.skipped_duplicates || 0} duplicates skipped</div>
    </div></div>
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Last Updated</div>
      <div class="activity-meta">${esc(vm.generated_at || '—')}</div>
    </div></div>
  `);
}

function renderRetrieval(d) {
  const ret = d.retrieval || {};
  const results = ret.results || {};
  const payload = ret.context_injection_payload || {};
  const queries = Object.keys(results).length;
  const totalHits = Object.values(results).reduce((s, r) => s + (r.memory_count || 0), 0);

  set('retrieval-cards', `
    <div class="card"><div class="card-label">Queries Run</div><div class="card-value">${queries}</div></div>
    <div class="card"><div class="card-label">Total Hits</div><div class="card-value" style="color:var(--green)">${totalHits}</div></div>
    <div class="card"><div class="card-label">Index Size</div><div class="card-value">${ret.index_size || 0} memories</div></div>
    <div class="card"><div class="card-label">Embedded</div><div class="card-value" style="color:var(--blue)">${ret.embedded_memories || 0}</div></div>
  `);

  const resultRows = Object.entries(results).slice(0, 6).map(([qid, r]) => {
    const synth = r.synthesis || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(qid.replace(/_/g,' '))} — ${r.memory_count || 0} hits</div>
      <div class="activity-meta">${esc(synth.synthesis || '').slice(0, 120)}</div>
      ${(synth.key_insights || []).slice(0, 1).map(i => `<div class="activity-meta" style="color:var(--blue)">→ ${esc(i).slice(0,100)}</div>`).join('')}
    </div></div>`;
  }).join('');
  set('retrieval-results', resultRows || '<div class="empty-state">No retrieval results yet — run vector_memory first</div>');

  const ctxRows = Object.entries(payload).slice(0, 4).map(([qid, ctx]) =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(qid.replace(/_/g,' '))}</div>
      <div class="activity-meta">${esc(ctx.summary || '').slice(0, 100)}</div>
      ${(ctx.top_matches || []).slice(0, 1).map(m => `<div class="activity-meta" style="color:var(--muted)">Score: ${m.score} — ${esc(m.text || '').slice(0, 80)}</div>`).join('')}
    </div></div>`
  ).join('');
  set('retrieval-context', ctxRows || '<div class="empty-state">No context payload yet</div>');
}

function renderToolRuntime(d) {
  const tr = d.tool_runtime || {};
  const catalog = tr.tool_catalog || {};
  const stats = tr.tool_stats || {};
  const ai = tr.ai_analysis || {};
  const tests = tr.test_results || {};
  const health = ai.runtime_health_score || 0;

  set('toolruntime-cards', `
    <div class="card"><div class="card-label">Runtime Health</div><div class="card-value" style="color:var(--${health>=70?'green':health>=40?'yellow':'red'})">${health}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Registered Tools</div><div class="card-value">${tr.registered_tools || Object.keys(catalog).length}</div></div>
    <div class="card"><div class="card-label">Tests Passed</div><div class="card-value" style="color:var(--green)">${Object.values(tests).filter(t=>t.success).length}/${Object.keys(tests).length}</div></div>
    <div class="card"><div class="card-label">Most Used</div><div class="card-value" style="font-size:13px">${esc(ai.most_used_tool || '—')}</div></div>
  `);

  const catRows = Object.entries(catalog).map(([name, def]) =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(name)} <span style="color:var(--${def.permission_level==='low'?'green':def.permission_level==='medium'?'yellow':'red'});font-size:11px">[${esc(def.permission_level)}]</span></div>
      <div class="activity-meta">${esc(def.description || '')} · ${def.rate_limit_per_hour}/hr</div>
    </div></div>`
  ).join('');
  set('toolruntime-catalog', catRows || '<div class="empty-state">No tools registered</div>');

  const statRows = Object.entries(stats).map(([tool, s]) =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(tool)} — ${s.success_rate_pct || 0}% success</div>
      <div class="activity-meta">${s.total_executions || 0} runs · avg ${s.avg_latency_ms || 0}ms · max ${s.max_latency_ms || 0}ms</div>
    </div></div>`
  ).join('');
  set('toolruntime-stats', statRows || '<div class="empty-state">No execution stats yet</div>');

  const analysisRows = [
    ai.reliability_summary ? `<div class="activity-item"><div class="activity-body"><div class="activity-meta">${esc(ai.reliability_summary)}</div></div></div>` : '',
    ...(ai.recommendations || []).map(r => `<div class="activity-item"><div class="activity-body"><div class="activity-meta" style="color:var(--blue)">→ ${esc(r)}</div></div></div>`),
    ...(ai.missing_tools_needed || []).map(t => `<div class="activity-item"><div class="activity-body"><div class="activity-meta" style="color:var(--yellow)">Missing: ${esc(t)}</div></div></div>`),
  ].join('');
  set('toolruntime-analysis', analysisRows || '<div class="empty-state">No analysis yet</div>');
}

function renderResearch(d) {
  const res = d.research || {};
  const projects = res.projects || {};
  const emerging = res.emerging_technologies || {};
  const pids = Object.keys(projects);

  set('research-cards', `
    <div class="card"><div class="card-label">Projects Researched</div><div class="card-value">${res.projects_researched || 0}</div></div>
    <div class="card"><div class="card-label">Competitors Analyzed</div><div class="card-value" style="color:var(--blue)">${res.total_competitors_analyzed || 0}</div></div>
    <div class="card"><div class="card-label">Trending Tech</div><div class="card-value">${(emerging.trending_technologies || []).length}</div></div>
    <div class="card"><div class="card-label">Top Research Score</div><div class="card-value" style="color:var(--green)">${Math.max(...pids.map(p => (projects[p].ai_synthesis || {}).research_score || 0), 0)}/100</div></div>
  `);

  const compRows = pids.flatMap(pid =>
    (projects[pid].competitor_signals || []).slice(0, 2).map(sig =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(sig.domain)} — ${esc(pid)}</div>
        <div class="activity-meta">${sig.reachable ? `✓ reachable · "${esc(sig.title || '').slice(0,60)}"` : '✗ unreachable'} · tech: ${(sig.tech_hints||[]).join(', ')||'none'}</div>
      </div></div>`
    )
  ).join('');
  set('research-competitors', compRows || '<div class="empty-state">No competitor data yet — workflow not yet run</div>');

  const rankRows = pids.map(pid => {
    const opps = (projects[pid].ranking_opportunities || {}).opportunities || [];
    return opps.slice(0, 2).map(o =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(pid)} — ${esc(o.type || '')}</div>
        <div class="activity-meta">${esc(o.keyword || o.topic || '')} · +${(o.potential_monthly_visits || o.estimated_traffic || 0).toLocaleString()} visits · <span style="color:var(--${(o.priority||'')=='high'?'green':'yellow'})">${esc(o.priority||'')}</span></div>
      </div></div>`
    ).join('');
  }).join('');
  set('research-rankings', rankRows || '<div class="empty-state">No ranking data yet</div>');

  const techRows = (emerging.trending_technologies || []).map(t =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(t.tech)}</div>
      <div class="activity-meta">${t.competitor_adoption} competitors using it</div>
    </div></div>`
  ).join('');
  set('research-tech', techRows || '<div class="empty-state">No tech signals yet</div>');

  const synthRows = pids.map(pid => {
    const s = projects[pid].ai_synthesis || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — score ${s.research_score || 0}/100</div>
      <div class="activity-meta">${esc(s.biggest_competitive_opportunity || '')}</div>
      ${(s.ux_quick_wins || []).slice(0,2).map(w => `<div class="activity-meta" style="color:var(--green)">→ ${esc(w)}</div>`).join('')}
    </div></div>`;
  }).join('');
  set('research-synthesis', synthRows || '<div class="empty-state">No synthesis yet</div>');
}

function renderSandbox(d) {
  const sb = d.sandbox || {};
  const experiments = sb.experiment_templates || [];
  const active = sb.active_sandbox_list || [];
  const ai = sb.ai_recommendations || {};

  set('sandbox-cards', `
    <div class="card"><div class="card-label">Active Sandboxes</div><div class="card-value" style="color:var(--blue)">${sb.active_sandboxes || 0}</div></div>
    <div class="card"><div class="card-label">Checkpoints</div><div class="card-value" style="color:var(--green)">${sb.checkpoints_created || 0}</div></div>
    <div class="card"><div class="card-label">Experiments</div><div class="card-value">${experiments.length}</div></div>
    <div class="card"><div class="card-label">Expired This Cycle</div><div class="card-value" style="color:var(--muted)">${sb.expired_this_cycle || 0}</div></div>
  `);

  const activeRows = active.length
    ? active.map(s =>
        `<div class="activity-item"><div class="activity-body">
          <div class="activity-title">${esc(s.id || '')} [${esc(s.type || '')}]</div>
          <div class="activity-meta">Risk: ${esc(s.risk_level || '')} · Files: ${(s.snapshotted_files || []).join(', ')} · Expires in ${s.auto_expire_hours || 0}h</div>
        </div></div>`
      ).join('')
    : '<div class="empty-state">No active sandboxes</div>';
  set('sandbox-active', activeRows);

  const expRows = experiments.map(e =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(e.id)} [${esc(e.type || '')}] — design score ${e.design_score || 0}/100</div>
      <div class="activity-meta">${esc(e.hypothesis || '')}</div>
      <div class="activity-meta" style="color:var(--green)">Success: ${esc(e.success_criteria || '')}</div>
      <div class="activity-meta" style="color:var(--red)">Rollback if: ${esc(e.rollback_condition || '')}</div>
    </div></div>`
  ).join('');
  set('sandbox-experiments', expRows || '<div class="empty-state">No experiments yet</div>');

  set('sandbox-recs', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Next recommended: ${esc(ai.recommended_next_experiment || '—')}</div>
      <div class="activity-meta">${esc(ai.reasoning || '')}</div>
      <div class="activity-meta" style="color:var(--${(ai.risk_assessment||'')==='low'?'green':'yellow'})">Risk: ${esc(ai.risk_assessment || '')}</div>
      <div class="activity-meta">Velocity: ${esc(ai.experiment_velocity || '')}</div>
    </div></div>
    ${(ai.expected_learnings || []).map(l => `<div class="activity-item"><div class="activity-body"><div class="activity-meta" style="color:var(--blue)">→ ${esc(l)}</div></div></div>`).join('')}
  `);
}

function renderObservability(d) {
  const obs = d.observability || {};
  const score = obs.observability_score || 0;
  const opStatus = obs.operational_status || 'unknown';
  const workflows = obs.workflow_metrics || [];
  const heatmap = obs.agent_heatmap || {};
  const bottlenecks = obs.bottlenecks || [];
  const errors = obs.error_propagation || [];
  const ai = obs.ai_analysis || {};
  const fresh = obs.fresh_workflow_count || 0;
  const stale = obs.stale_workflow_count || 0;
  const statusColor = opStatus === 'green' ? 'green' : opStatus === 'yellow' ? 'yellow' : 'red';

  set('observability-cards', `
    <div class="card"><div class="card-label">Observability Score</div><div class="card-value" style="color:var(--${statusColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Operational Status</div><div class="card-value" style="color:var(--${statusColor})">${esc(opStatus.toUpperCase())}</div></div>
    <div class="card"><div class="card-label">Fresh Workflows</div><div class="card-value" style="color:var(--green)">${fresh}/${fresh+stale}</div></div>
    <div class="card"><div class="card-label">Active Bottlenecks</div><div class="card-value" style="color:var(--${bottlenecks.length>0?'yellow':'green'})">${bottlenecks.length}</div></div>
  `);

  const wfRows = workflows.slice(0, 10).map(wf => {
    const sc = wf.status === 'fresh' ? 'green' : wf.status === 'stale' ? 'yellow' : 'red';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--${sc})">${esc(wf.workflow)} [${esc(wf.status||'')}]</div>
      <div class="activity-meta">${wf.age_hours !== null ? `${wf.age_hours}h ago` : 'never run'} · $${(wf.cost_usd||0).toFixed(4)} · ${(wf.tokens_used||0).toLocaleString()} tokens</div>
    </div></div>`;
  }).join('');
  set('observability-workflows', wfRows || '<div class="empty-state">No workflow metrics yet</div>');

  const hmRows = Object.entries(heatmap).map(([agent, data]) => {
    const ac = data.activity_level === 'high' ? 'green' : data.activity_level === 'medium' ? 'blue' : 'muted';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(agent)} — <span style="color:var(--${ac})">${esc(data.activity_level || '')}</span></div>
      <div class="activity-meta">${data.total_missions || 0} missions · ${Math.round((data.success_rate || 0) * 100)}% success · confidence ${Math.round((data.confidence || 0) * 100)}%</div>
    </div></div>`;
  }).join('');
  set('observability-heatmap', hmRows || '<div class="empty-state">No agent data yet</div>');

  const errRows = [
    ...bottlenecks.map(b =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title" style="color:var(--${b.severity==='critical'?'red':'yellow'})">${esc(b.type.replace(/_/g,' '))} [${esc(b.severity)}]</div>
        <div class="activity-meta">${esc(b.details)}</div>
      </div></div>`
    ),
    ...errors.slice(0, 4).map(e =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title" style="color:var(--${e.severity==='high'?'red':e.severity==='medium'?'yellow':'muted'})">${esc(e.source)} — ${esc(e.project)}</div>
        <div class="activity-meta">${esc(e.error || '')}</div>
      </div></div>`
    ),
  ].join('');
  set('observability-errors', errRows || '<div class="empty-state" style="color:var(--green)">No bottlenecks or errors detected</div>');

  set('observability-analysis', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-meta">${esc(ai.executive_summary || '')}</div>
    </div></div>
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Top Bottleneck</div>
      <div class="activity-meta">${esc(ai.top_bottleneck || 'None')}</div>
    </div></div>
    ${(ai.next_actions || []).map(a => `<div class="activity-item"><div class="activity-body"><div class="activity-meta" style="color:var(--blue)">→ ${esc(a)}</div></div></div>`).join('')}
  `);
}

// ─── Phase I: Business Growth ────────────────────────────────────────────────

function renderGrowth(d) {
  const g = d.growth || {};
  const score = g.portfolio_growth_score || 0;
  const backlinks = g.total_backlink_opportunities || 0;
  const schema = g.total_schema_opportunities || 0;
  const quickWins = g.all_quick_wins || [];
  const projects = g.projects || {};

  set('growth-cards', `
    <div class="card"><div class="card-label">Portfolio Growth Score</div><div class="card-value">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Backlink Opportunities</div><div class="card-value" style="color:var(--green)">${backlinks}</div></div>
    <div class="card"><div class="card-label">Schema Opportunities</div><div class="card-value" style="color:var(--blue)">${schema}</div></div>
    <div class="card"><div class="card-label">Projects Analyzed</div><div class="card-value">${Object.keys(projects).length}</div></div>
  `);

  const blRows = Object.entries(projects).flatMap(([pid, p]) =>
    (p.backlink_opportunities || []).slice(0, 2).map(b =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(b.type.replace(/_/g,' '))} — ${esc(pid)}</div>
        <div class="activity-meta">${esc(b.approach)} · ~${b.estimated_links || 0} links · <span style="color:var(--${b.priority==='high'?'red':b.priority==='medium'?'yellow':'muted'})">${esc(b.priority)}</span></div>
      </div></div>`
    )
  ).join('');
  set('growth-backlinks', blRows || '<div class="empty-state">No backlink data yet</div>');

  const authRows = Object.entries(projects).flatMap(([pid, p]) =>
    (p.topical_authority_plan || []).slice(0, 2).map(a =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(a.pillar.replace(/_/g,' '))} — ${esc(pid)}</div>
        <div class="activity-meta">${a.recommended_articles} articles · +${(a.estimated_traffic_gain||0).toLocaleString()} est visits · <span style="color:var(--${a.status==='not_started'?'red':'yellow'})">${esc(a.status)}</span></div>
      </div></div>`
    )
  ).join('');
  set('growth-authority', authRows || '<div class="empty-state">No authority data yet</div>');

  const schemaRows = Object.entries(projects).flatMap(([pid, p]) =>
    (p.schema_opportunities || []).slice(0, 2).map(s =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(s.schema)} — ${esc(pid)}</div>
        <div class="activity-meta">+${s.ctr_boost_pct}% CTR · ${s.applicable_pages} pages · effort: ${esc(s.effort)}</div>
      </div></div>`
    )
  ).join('');
  set('growth-schema', schemaRows || '<div class="empty-state">No schema data yet</div>');

  const qwRows = quickWins.slice(0, 6).map(qw =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--green)">${esc(qw.action)}</div>
      <div class="activity-meta">${esc(qw.impact)} · ${qw.timeline_days}d · <span style="color:var(--blue)">${esc(qw.project||'')}</span></div>
    </div></div>`
  ).join('');
  set('growth-quickwins', qwRows || '<div class="empty-state">No quick wins yet</div>');

  const stratRows = Object.entries(projects).map(([pid, p]) => {
    const s = p.ai_strategy || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — SEO score ${s.seo_growth_score||0}/100 · ${s['90_day_traffic_multiplier']||1}x traffic target</div>
      <div class="activity-meta">${esc(s.primary_growth_lever||'')}</div>
      <div class="activity-meta" style="margin-top:4px">${esc(s.executive_summary||'')}</div>
    </div></div>`;
  }).join('');
  set('growth-strategy', stratRows || '<div class="empty-state">No strategy data yet</div>');
}

function renderRevenue(d) {
  const m = d.monetization_runtime || {};
  const current = m.portfolio_current_revenue_usd || 0;
  const target = m.portfolio_target_revenue_usd || 0;
  const gap = m.portfolio_revenue_gap_usd || 0;
  const projects = m.projects || {};
  const pct = target > 0 ? Math.min(Math.round(current / target * 100), 100) : 0;

  set('revenue-cards', `
    <div class="card"><div class="card-label">Current Monthly Revenue</div><div class="card-value" style="color:var(--green)">$${current.toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Portfolio Target</div><div class="card-value">$${target.toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Revenue Gap</div><div class="card-value" style="color:var(--red)">$${gap.toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Target Achieved</div><div class="card-value" style="color:var(--${pct>=80?'green':pct>=40?'yellow':'red'})">${pct}%</div></div>
  `);

  const yp = projects.yallaplays || {};
  const ypImpl = yp.implementations || {};
  const ypAds = ypImpl.adsense || {};
  set('revenue-yallaplays', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Model: ${esc(yp.model||'ad-supported')}</div>
      <div class="activity-meta">Est revenue: <strong>$${(yp.current_revenue_est_usd||0).toFixed(0)}/mo</strong> → target $${(yp.monthly_target_usd||0).toLocaleString()}</div>
      ${ypAds.current_rpm !== undefined ? `<div class="activity-meta">RPM: $${ypAds.current_rpm} → $${ypAds.target_rpm} (gap $${ypAds.rpm_gap})</div>` : ''}
      <div class="activity-meta" style="color:var(--blue)">${esc((yp.ai_plan||{}).top_revenue_action||'')}</div>
    </div></div>
  `);

  const fi = projects.fionera || {};
  const fiImpl = fi.implementations || {};
  const fiPrem = fiImpl.premium_conversion || {};
  set('revenue-fionera', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Model: ${esc(fi.model||'freemium')}</div>
      <div class="activity-meta">Est revenue: <strong>$${(fi.current_revenue_est_usd||0).toFixed(0)}/mo</strong> → target $${(fi.monthly_target_usd||0).toLocaleString()}</div>
      ${fiPrem.monthly_price ? `<div class="activity-meta">Price: $${fiPrem.monthly_price}/mo · $${fiPrem.annual_price}/yr (save ${fiPrem.annual_discount_pct}%)</div>` : ''}
      <div class="activity-meta" style="color:var(--blue)">${esc((fi.ai_plan||{}).top_revenue_action||'')}</div>
    </div></div>
  `);

  const mi = projects.mifteh || {};
  const miImpl = mi.implementations || {};
  const miLead = miImpl.lead_funnel || {};
  set('revenue-mifteh', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Model: ${esc(mi.model||'b2b-services')}</div>
      <div class="activity-meta">Est revenue: <strong>$${(mi.current_revenue_est_usd||0).toFixed(0)}/mo</strong> → target $${(mi.monthly_target_usd||0).toLocaleString()}</div>
      ${miLead.lead_magnet ? `<div class="activity-meta">Lead magnet: ${esc(miLead.lead_magnet)}</div>` : ''}
      <div class="activity-meta" style="color:var(--blue)">${esc((mi.ai_plan||{}).top_revenue_action||'')}</div>
    </div></div>
  `);

  const planRows = Object.entries(projects).map(([pid, p]) => {
    const plan = p.ai_plan || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — M1 $${(plan.month_1_revenue_target_usd||0).toFixed(0)} · M3 $${(plan.month_3_revenue_target_usd||0).toFixed(0)}</div>
      <div class="activity-meta">${esc(plan.pricing_optimization||'')}</div>
      <div class="activity-meta" style="color:var(--muted)">${esc(plan.revenue_gap_strategy||'')}</div>
    </div></div>`;
  }).join('');
  set('revenue-plans', planRows || '<div class="empty-state">No revenue plan data yet</div>');
}

function renderConversions(d) {
  const c = d.conversion || {};
  const score = c.portfolio_cro_score || 0;
  const projects = c.projects || {};
  const pids = Object.keys(projects);

  set('conversions-cards', `
    <div class="card"><div class="card-label">Portfolio CRO Score</div><div class="card-value" style="color:var(--${score>=70?'green':score>=45?'yellow':'red'})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Projects Optimized</div><div class="card-value">${pids.length}</div></div>
    <div class="card"><div class="card-label">Conversion Goals</div><div class="card-value">${pids.map(p => (projects[p].primary_conversion||'').replace(/_/g,' ')).filter(Boolean).length}</div></div>
    <div class="card"><div class="card-label">30-Day Lift Target</div><div class="card-value" style="color:var(--green)">${Math.max(...pids.map(p=>(projects[p].ai_recommendations||{})['30_day_conversion_lift_pct']||0))}%</div></div>
  `);

  const funnelRows = pids.map(pid => {
    const funnel = (projects[pid].funnel_analysis || {});
    const stages = funnel.stages || [];
    const biggest = funnel.biggest_drop_stage || '';
    const endRate = funnel.end_conversion_rate_pct || 0;
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — end rate ${endRate.toFixed(1)}%</div>
      <div class="activity-meta">Biggest drop: <span style="color:var(--red)">${esc(biggest)}</span> (${funnel.biggest_drop_pct||0}% lost)</div>
      ${stages.slice(0,3).map(s=>`<div class="activity-meta" style="margin-left:8px">• ${esc(s.stage)}: ${s.visitors_pct}% → drop ${s.drop_off_pct}%</div>`).join('')}
    </div></div>`;
  }).join('');
  set('conversions-funnel', funnelRows || '<div class="empty-state">No funnel data yet</div>');

  const ctaRows = pids.map(pid => {
    const cta = (projects[pid].cta_optimization || {});
    const variants = cta.cta_variants || [];
    const test = cta.recommended_ab_test || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — Goal: ${esc(cta.primary_conversion_goal||'').replace(/_/g,' ')}</div>
      ${variants.slice(0,2).map(v=>`<div class="activity-meta">• "${esc(v.text)}" → ${v.placement} · +${Math.round((v.estimated_ctr_boost||0)*100)}% CTR</div>`).join('')}
      ${test.control ? `<div class="activity-meta" style="color:var(--blue)">A/B: "${esc(test.control)}" vs "${esc(test.variant_a)}" · ${test.test_duration_days}d</div>` : ''}
    </div></div>`;
  }).join('');
  set('conversions-cta', ctaRows || '<div class="empty-state">No CTA data yet</div>');

  const rpvRows = pids.map(pid => {
    const rpv = (projects[pid].revenue_per_visit || {});
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — $${rpv.current_rpv_usd||0} RPV → $${rpv.target_rpv_usd||0} target</div>
      <div class="activity-meta">Gap: $${rpv.rpv_gap_usd||0} · Need ${rpv.rpv_multiplier_needed||1}x · ${(rpv.monthly_sessions||0).toLocaleString()} sessions/mo</div>
    </div></div>`;
  }).join('');
  set('conversions-rpv', rpvRows || '<div class="empty-state">No RPV data yet</div>');

  const recRows = pids.map(pid => {
    const recs = (projects[pid].ai_recommendations || {});
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — CRO ${recs.cro_score||0}/100</div>
      <div class="activity-meta" style="color:var(--green)">${esc(recs.top_priority_fix||'')}</div>
      ${(recs.quick_wins||[]).slice(0,2).map(q=>`<div class="activity-meta">• ${esc(q.action)} — ${esc(q.impact)}</div>`).join('')}
    </div></div>`;
  }).join('');
  set('conversions-recs', recRows || '<div class="empty-state">No CRO recs yet</div>');
}

function renderAcquisition(d) {
  const a = d.acquisition || {};
  const m1 = a.portfolio_month_1_session_target || 0;
  const m3 = a.portfolio_month_3_session_target || 0;
  const projects = a.projects || {};
  const pids = Object.keys(projects);

  set('acquisition-cards', `
    <div class="card"><div class="card-label">M1 Session Target</div><div class="card-value" style="color:var(--green)">${m1.toLocaleString()}</div></div>
    <div class="card"><div class="card-label">M3 Session Target</div><div class="card-value" style="color:var(--blue)">${m3.toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Campaigns Planned</div><div class="card-value">${pids.length}</div></div>
    <div class="card"><div class="card-label">Growth Loops</div><div class="card-value">${pids.reduce((s,p)=>s+(projects[p].growth_loops||[]).length,0)}</div></div>
  `);

  const viralRows = pids.flatMap(pid =>
    (projects[pid].viral_content_plan || []).slice(0, 2).map(v =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(v.format.replace(/_/g,' '))} — ${esc(pid)}</div>
        <div class="activity-meta">${esc(v.hook)} · ~${(v.estimated_reach||0).toLocaleString()} reach · virality ${v.virality_score} · <span style="color:var(--blue)">${esc(v.primary_platform)}</span></div>
      </div></div>`
    )
  ).join('');
  set('acquisition-viral', viralRows || '<div class="empty-state">No viral content data yet</div>');

  const clusterRows = pids.map(pid => {
    const cl = projects[pid].seo_cluster_expansion || {};
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(pid)} — ${cl.current_clusters||0} → ${cl.target_clusters||0} clusters</div>
      <div class="activity-meta">+${cl.new_pages_planned||0} new pages planned</div>
      ${(cl.cluster_plan||[]).slice(0,2).map(c=>`<div class="activity-meta">• ${esc(c.pillar)} — +${(c.estimated_traffic_gain||0).toLocaleString()} visits · ${c.timeline_weeks}w</div>`).join('')}
    </div></div>`;
  }).join('');
  set('acquisition-clusters', clusterRows || '<div class="empty-state">No cluster data yet</div>');

  const loopRows = pids.flatMap(pid =>
    (projects[pid].growth_loops || []).slice(0, 2).map(l =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(l.loop_name.replace(/_/g,' '))} — ${esc(pid)}</div>
        <div class="activity-meta">K-factor ${l.viral_coefficient} · -${l.cac_reduction_pct}% CAC · ${esc(l.implementation_complexity)} effort</div>
      </div></div>`
    )
  ).join('');
  set('acquisition-loops', loopRows || '<div class="empty-state">No growth loop data yet</div>');

  const outRows = pids.flatMap(pid =>
    (projects[pid].outreach_plan || []).slice(0, 2).map(o =>
      `<div class="activity-item"><div class="activity-body">
        <div class="activity-title">${esc(o.type.replace(/_/g,' '))} — ${esc(pid)}</div>
        <div class="activity-meta">${o.target_count} targets · ${(o.estimated_total_reach||0).toLocaleString()} reach · ${o.timeline_weeks}w · <span style="color:var(--${o.priority==='high'?'green':'yellow'})">${esc(o.priority)}</span></div>
      </div></div>`
    )
  ).join('');
  set('acquisition-outreach', outRows || '<div class="empty-state">No outreach data yet</div>');
}

function renderScaling(d) {
  const s = d.scaling || {};
  const health = (s.ai_analysis || {}).system_health_score || 0;
  const status = (s.ai_analysis || {}).scaling_status || 'unknown';
  const storage = s.storage || {};
  const tokens = s.token_usage || {};
  const workload = s.workload_balance || {};
  const opts = s.optimizations || [];

  const statusColor = status === 'healthy' ? 'green' : status === 'degraded' ? 'yellow' : 'red';
  set('scaling-cards', `
    <div class="card"><div class="card-label">System Health</div><div class="card-value" style="color:var(--${statusColor})">${health}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Scaling Status</div><div class="card-value" style="color:var(--${statusColor})">${esc(status.toUpperCase())}</div></div>
    <div class="card"><div class="card-label">Total Storage</div><div class="card-value" style="color:var(--${(storage.total_mb||0)>50?'yellow':'green'})">${(storage.total_mb||0).toFixed(1)} MB</div></div>
    <div class="card"><div class="card-label">Token Budget Used</div><div class="card-value" style="color:var(--${(tokens.budget_used_pct||0)>100?'red':(tokens.budget_used_pct||0)>70?'yellow':'green'})">${tokens.budget_used_pct||0}%</div></div>
  `);

  const byScript = tokens.by_script || {};
  const tokenRows = Object.entries(byScript).sort((a,b)=>b[1].cost_usd-a[1].cost_usd).slice(0,8).map(([script, t]) =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(script.replace(/_/g,' '))}</div>
      <div class="activity-meta">${(t.tokens||0).toLocaleString()} tokens · $${(t.cost_usd||0).toFixed(4)}</div>
    </div></div>`
  ).join('');
  set('scaling-tokens', tokenRows || '<div class="empty-state">No token data yet — workflows not yet run</div>');

  const mem = storage.memory || {};
  const largestFiles = (mem.largest_files || []).slice(0, 5);
  const storageRows = [
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">Memory Directory</div><div class="activity-meta">${(mem.total_mb||0).toFixed(1)} MB · ${mem.file_count||0} files · <span style="color:var(--${mem.warning?'red':'green'})">${mem.status||'ok'}</span></div></div></div>`,
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">Outputs Directory</div><div class="activity-meta">${((storage.outputs||{}).total_mb||0).toFixed(1)} MB · ${(storage.outputs||{}).output_count||0} files</div></div></div>`,
    ...largestFiles.map(f => `<div class="activity-item"><div class="activity-body"><div class="activity-meta">${esc(f.file)} — ${f.size_kb} KB</div></div></div>`),
  ].join('');
  set('scaling-storage', storageRows || '<div class="empty-state">No storage data yet</div>');

  const byCat = workload.by_category || {};
  const wfRows = [
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">Total Workflows: ${workload.total_workflows||0}</div>
      <div class="activity-meta">${workload.daily_workflow_runs||0} daily · ${workload.weekly_workflow_runs||0} weekly · ${workload.schedule_spread_hours||0} spread hours</div>
    </div></div>`,
    ...Object.entries(byCat).map(([cat, count]) =>
      `<div class="activity-item"><div class="activity-body"><div class="activity-meta">${esc(cat)}: ${count} workflows</div></div></div>`
    ),
  ].join('');
  set('scaling-workflows', wfRows || '<div class="empty-state">No workflow data yet</div>');

  const optRows = opts.map(o =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--${o.priority==='high'?'red':o.priority==='medium'?'yellow':'muted'})">${esc(o.type.replace(/_/g,' '))} [${esc(o.priority)}]</div>
      <div class="activity-meta">${esc(o.action)}</div>
      <div class="activity-meta" style="color:var(--green)">Savings: ${esc(o.savings_estimate)}</div>
    </div></div>`
  ).join('');
  set('scaling-optimizations', optRows || '<div class="empty-state">No optimizations identified</div>');
}

// ─── Phase K: Business Execution ─────────────────────────────────────────────

function renderKpiTracker(d) {
  const k = d.kpi_tracker || {};
  const portfolio = k.portfolio || {};
  const ai = k.ai_analysis || {};
  const projects = k.projects || {};
  const score = k.kpi_score || portfolio.portfolio_kpi_score || 0;
  const status = portfolio.overall_status || 'unknown';
  const statusColor = status === 'green' ? 'green' : status === 'yellow' ? 'yellow' : 'red';

  set('kpi-cards', `
    <div class="card"><div class="card-label">KPI Score</div><div class="card-value" style="color:var(--${statusColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">On Track</div><div class="card-value" style="color:var(--green)">${portfolio.on_track_kpis||0}<span style="font-size:14px;color:var(--muted)"> / ${portfolio.total_kpis_tracked||0}</span></div></div>
    <div class="card"><div class="card-label">Alerts</div><div class="card-value" style="color:var(--${(portfolio.kpis_behind||0)>0?'red':'green'})">${portfolio.kpis_behind||0}</div></div>
    <div class="card"><div class="card-label">Momentum</div><div class="card-value" style="color:var(--blue)">${esc(ai.growth_momentum||'stable')}</div></div>
  `);

  const renderProjectKpis = (proj, label, elId) => {
    const pr = (projects[proj] || {});
    const kpis = pr.kpis || {};
    const rows = Object.entries(kpis).map(([name, v]) => {
      const bar = Math.min(100, v.attainment_pct || 0);
      const col = v.status === 'on_track' ? 'green' : v.status === 'warning' ? 'yellow' : 'red';
      return `<div class="activity-item"><div class="activity-body">
        <div class="activity-title" style="display:flex;justify-content:space-between">
          <span>${esc(name.replace(/_/g,' '))}</span>
          <span style="color:var(--${col})">${bar.toFixed(0)}%</span>
        </div>
        <div class="activity-meta">${esc(String(v.actual))} ${esc(v.unit||'')} → target ${esc(String(v.target))}</div>
        <div style="height:3px;background:#1e293b;border-radius:2px;margin-top:4px"><div style="height:3px;width:${bar}%;background:var(--${col});border-radius:2px"></div></div>
      </div></div>`;
    }).join('');
    set(elId, rows || `<div class="empty-state">${esc(label)} KPIs not yet tracked</div>`);
  };

  renderProjectKpis('yallaplays', 'YallaPlays', 'kpi-yallaplays');
  renderProjectKpis('fionera', 'Fionera', 'kpi-fionera');
  renderProjectKpis('mifteh', 'Mifteh', 'kpi-mifteh');

  const alerts = (portfolio.active_alerts || []).slice(0, 6);
  const wins = (ai.quick_wins || []).slice(0, 4);
  set('kpi-alerts', [
    ...alerts.map(a => `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--red)">⚠ ${esc(a)}</div></div></div>`),
    ...wins.map(w => `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✦ ${esc(w.kpi||'')} — ${esc(w.action||'')}</div><div class="activity-meta">${esc(w.impact||'')}</div></div></div>`),
  ].join('') || '<div class="empty-state">No alerts — all KPIs healthy</div>');

  const fc = ai.forecast_30_days || {};
  set('kpi-forecast', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">YallaPlays Sessions</div><div class="activity-meta">${(fc.yallaplays_sessions||0).toLocaleString()} / month</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Fionera MRR</div><div class="activity-meta">$${(fc.fionera_mrr_usd||0).toFixed(0)}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Mifteh Leads</div><div class="activity-meta">${fc.mifteh_leads||0} leads</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Portfolio Attainment</div><div class="activity-meta">${(fc.portfolio_attainment_pct||0).toFixed(1)}%</div></div></div>
    ${k.executive_summary ? `<div class="activity-item"><div class="activity-body"><div class="activity-meta" style="color:var(--dim)">${esc(k.executive_summary)}</div></div></div>` : ''}
  `);
}

function renderRoiAgent(d) {
  const r = d.roi_agent || {};
  const queue = r.execution_queue || {};
  const score = r.strategy_score || 0;
  const scoreColor = score >= 70 ? 'green' : score >= 40 ? 'yellow' : 'red';

  set('roi-cards', `
    <div class="card"><div class="card-label">Strategy Score</div><div class="card-value" style="color:var(--${scoreColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Actions Ranked</div><div class="card-value" style="color:var(--blue)">${r.total_actions_ranked||0}</div></div>
    <div class="card"><div class="card-label">Total Pipeline</div><div class="card-value" style="color:var(--green)">$${((r.total_pipeline_usd||0)/1000).toFixed(1)}K</div></div>
    <div class="card"><div class="card-label">Top Priority</div><div class="card-value" style="font-size:12px;color:var(--yellow)">${esc((r.top_priority_action||'').slice(0,30))}…</div></div>
  `);

  const renderActionList = (actions, elId) => {
    const rows = (actions || []).slice(0, 8).map(a => {
      const scoreColor = a.roi_score >= 70 ? 'green' : a.roi_score >= 40 ? 'yellow' : 'red';
      return `<div class="activity-item"><div class="activity-body">
        <div class="activity-title" style="display:flex;justify-content:space-between">
          <span>${esc(a.action||'').slice(0,55)}</span>
          <span style="color:var(--${scoreColor})">${a.roi_score||0}</span>
        </div>
        <div class="activity-meta">[${esc(a.project||'')}] $${(a.revenue_impact_usd||0).toFixed(0)} impact · ${a.time_to_value_weeks||0}w</div>
      </div></div>`;
    }).join('');
    set(elId, rows || '<div class="empty-state">No actions yet — run ROI prioritizer</div>');
  };

  renderActionList(queue.immediate, 'roi-immediate');
  renderActionList(queue.this_week, 'roi-week');

  const directives = r.agent_directives || {};
  set('roi-directives', Object.entries(directives).map(([agent, directive]) =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(agent.replace(/_/g,' '))}</div><div class="activity-meta">${esc(directive)}</div></div></div>`
  ).join('') || '<div class="empty-state">No directives generated yet</div>');

  const sequence = r.revenue_unlock_sequence || [];
  set('roi-sequence', sequence.map(s =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">${esc(s)}</div></div></div>`
  ).join('') || `<div class="empty-state">${esc(r.execution_philosophy||'No sequence yet')}</div>`);
}

function renderProgSeo(d) {
  const s = d.programmatic_seo || {};
  const score = s.seo_score || 0;
  const scoreColor = score >= 70 ? 'green' : score >= 40 ? 'yellow' : 'red';
  const estTraffic = s.estimated_monthly_traffic_gain || 0;

  set('prog-seo-cards', `
    <div class="card"><div class="card-label">SEO Score</div><div class="card-value" style="color:var(--${scoreColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Pages Generated</div><div class="card-value" style="color:var(--blue)">${(s.total_pages_generated||0).toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Est. Traffic Gain</div><div class="card-value" style="color:var(--green)">+${estTraffic.toLocaleString()}/mo</div></div>
    <div class="card"><div class="card-label">Authority Status</div><div class="card-value" style="font-size:12px;color:var(--yellow)">${esc(s.authority_building_status||'pending')}</div></div>
  `);

  set('prog-seo-types', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Category Hub Pages</div><div class="activity-meta">${s.hub_pages_count||0} pages generated</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Long-Tail Pages</div><div class="activity-meta">${s.long_tail_pages_count||0} pages generated</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">FAQ Rich Pages</div><div class="activity-meta">${s.faq_pages_count||0} pages with schema markup</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Comparison Pages</div><div class="activity-meta">${s.comparison_pages_count||0} competitor comparisons</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Trending Pages</div><div class="activity-meta">${s.trending_pages_count||0} trending topic pages</div></div></div>
  `);

  const opps = s.top_opportunities || [];
  set('prog-seo-opps', opps.map(o =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">◈ ${esc(o)}</div></div></div>`
  ).join('') || '<div class="empty-state">Run programmatic SEO workflow to populate</div>');

  set('prog-seo-authority', `<div class="activity-item"><div class="activity-body">
    <div class="activity-title">Status: ${esc(s.authority_building_status||'pending')}</div>
    <div class="activity-meta">${esc(s.executive_summary||'Awaiting first workflow run')}</div>
  </div></div>`);

  const next = s.next_priorities || [];
  set('prog-seo-next', next.map((n,i) =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">${i+1}. ${esc(n)}</div></div></div>`
  ).join('') || '<div class="empty-state">No priorities generated yet</div>');
}

function renderProductBuilder(d) {
  const pb = d.product_builder || {};
  const bist = (pb.features_built||0);
  const realData = pb.has_real_market_data;

  set('product-builder-cards', `
    <div class="card"><div class="card-label">Features Built</div><div class="card-value" style="color:var(--blue)">${bist}</div></div>
    <div class="card"><div class="card-label">Real Market Data</div><div class="card-value" style="color:var(--${realData?'green':'yellow'})">${realData?'LIVE':'ESTIMATED'}</div></div>
    <div class="card"><div class="card-label">BIST Symbols</div><div class="card-value" style="color:var(--green)">${pb.bist_symbols_tracked||0}</div></div>
    <div class="card"><div class="card-label">Stock Analyses</div><div class="card-value" style="color:var(--blue)">${pb.stock_analyses||0}</div></div>
  `);

  const bistPage = pb.bist_market_page || {};
  const topGainers = bistPage.top_gainers || [];
  set('product-bist', [
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">Sentiment: ${esc(bistPage.market_sentiment||'N/A')}</div><div class="activity-meta">${esc(bistPage.sentiment_reason||'')}</div></div></div>`,
    ...topGainers.slice(0,4).map(g =>
      `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">${esc(g.symbol||'')} — ${esc(g.name||'')}</div><div class="activity-meta">+${esc(String(g.change_pct||0))}% · ${esc(g.signal||'')}</div></div></div>`
    ),
  ].join('') || '<div class="empty-state">No BIST data yet — run product builder workflow</div>');

  const cryptoPage = pb.crypto_movers || {};
  const movers = cryptoPage.top_movers || [];
  set('product-crypto', movers.slice(0,4).map(m =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(m.symbol||'')} — ${esc(m.tr_name||m.name||'')}</span>
        <span style="color:var(--${(m.change_24h_pct||0)>=0?'green':'red'})">${(m.change_24h_pct||0)>=0?'+':''}${esc(String(m.change_24h_pct||0))}%</span>
      </div>
      <div class="activity-meta">$${(m.price_usd||0).toLocaleString()} · ${esc(m.ai_signal||'')}</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No crypto data yet</div>');

  const roadmap = pb.product_roadmap || [];
  set('product-roadmap-items', roadmap.map((r,i) =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">${i+1}. ${esc(r)}</div></div></div>`
  ).join('') || '<div class="empty-state">No roadmap items yet</div>');

  const analyses = (pb.ai_stock_analyses || pb.stock_analyses_data || []);
  set('product-stocks', analyses.slice ? analyses.slice(0,4).map(a =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(a.symbol||'')} — ${esc(a.company_name||'')}</span>
        <span style="color:var(--${a.ai_rating==='buy'?'green':a.ai_rating==='sell'?'red':'yellow'})">${esc(a.ai_rating||'').toUpperCase()}</span>
      </div>
      <div class="activity-meta">Score ${a.fundamental_score||0} · ${esc(a.ai_summary||'').slice(0,80)}</div>
    </div></div>`
  ).join('') : '<div class="empty-state">No stock analyses yet</div>');
}

function renderClientAcquisition(d) {
  const ca = d.client_acquisition || {};
  const score = ca.estimated_monthly_leads || 0;
  const pipeline = ca.estimated_pipeline_value_usd || 0;

  set('client-acq-cards', `
    <div class="card"><div class="card-label">Monthly Leads Est.</div><div class="card-value" style="color:var(--green)">${score}</div></div>
    <div class="card"><div class="card-label">Pipeline Value</div><div class="card-value" style="color:var(--green)">$${(pipeline/1000).toFixed(1)}K</div></div>
    <div class="card"><div class="card-label">Service Pages</div><div class="card-value" style="color:var(--blue)">${ca.service_pages||0}</div></div>
    <div class="card"><div class="card-label">Case Studies</div><div class="card-value" style="color:var(--blue)">${ca.case_studies||0}</div></div>
  `);

  const tiers = [
    {name:'AI Starter', price:'$999/mo', ideal:'Small businesses & startups'},
    {name:'AI Growth', price:'$2,499/mo', ideal:'Growing companies targeting 10x traffic'},
    {name:'AI Enterprise', price:'$7,499/mo', ideal:'Enterprises demanding AI-first advantage'},
  ];
  set('client-acq-pricing', tiers.map(t =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(t.name)}</span><span style="color:var(--green)">${esc(t.price)}</span>
      </div>
      <div class="activity-meta">${esc(t.ideal)}</div>
    </div></div>`
  ).join(''));

  const magnets = ca.lead_magnets || 0;
  set('client-acq-magnets', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Free AI Growth Audit</div><div class="activity-meta">PDF report — delivers in 24h · 12% CVR expected</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">AI ROI Calculator</div><div class="activity-meta">Interactive tool — instant results · 20% CVR expected</div></div></div>
    ${magnets > 2 ? `<div class="activity-item"><div class="activity-body"><div class="activity-meta">+${magnets-2} additional lead magnets generated</div></div></div>` : ''}
  `);

  const cases = ca.case_studies || 0;
  set('client-acq-cases', cases > 0 ? `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">E-commerce SEO Growth</div><div class="activity-meta">+325% organic sessions · +325% revenue · 90 days</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">SaaS Traffic Scale</div><div class="activity-meta">+292% organic sessions · 90 days</div></div></div>
    ${cases > 2 ? `<div class="activity-item"><div class="activity-body"><div class="activity-meta">+${cases-2} more case studies generated</div></div></div>` : ''}
  ` : '<div class="empty-state">Run client acquisition workflow to generate case studies</div>');

  const clusters = ca.seo_clusters || 0;
  set('client-acq-clusters', clusters > 0 ? `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">AI Automation for E-commerce</div><div class="activity-meta">1,800 monthly searches · medium competition</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">AI SEO Tools for Small Business</div><div class="activity-meta">1,800 monthly searches · medium competition</div></div></div>
    ${clusters > 2 ? `<div class="activity-item"><div class="activity-body"><div class="activity-meta">+${clusters-2} more SEO clusters mapped</div></div></div>` : ''}
  ` : '<div class="empty-state">No SEO clusters yet</div>');
}

function renderAnalyticsSyncer(d) {
  const a = d.analytics_syncer || {};
  const score = a.analytics_health_score || 0;
  const scoreColor = score >= 70 ? 'green' : score >= 40 ? 'yellow' : 'red';
  const sources = a.sources_connected || [];

  set('analytics-syncer-cards', `
    <div class="card"><div class="card-label">Analytics Score</div><div class="card-value" style="color:var(--${scoreColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Sources Connected</div><div class="card-value" style="color:var(--blue)">${a.sources_count||sources.length}</div></div>
    <div class="card"><div class="card-label">Data Quality</div><div class="card-value" style="color:var(--${a.data_completeness==='high'?'green':a.data_completeness==='medium'?'yellow':'red'})">${esc((a.data_completeness||'low').toUpperCase())}</div></div>
    <div class="card"><div class="card-label">Stripe</div><div class="card-value" style="color:var(--${(a.stripe||{}).status!=='not_connected'?'green':'yellow'})">${(a.stripe||{}).status==='not_connected'?'NOT LINKED':'LINKED'}</div></div>
  `);

  const SOURCE_ICONS = {cloudflare:'☁',posthog:'◈',stripe:'💳',adsense:'$',analytics_intelligence:'◉',twelvedata:'📊'};
  set('analytics-syncer-sources', sources.map(s =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${SOURCE_ICONS[s]||'◎'} ${esc(s.replace(/_/g,' '))}</div>
      <div class="activity-meta" style="color:var(--green)">Connected</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No analytics sources connected yet</div>');

  const traffic = a.traffic_insights || {};
  set('analytics-syncer-traffic', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Monthly Pageviews</div><div class="activity-meta">${(traffic.total_monthly_pageviews||0).toLocaleString()}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Fastest Growing</div><div class="activity-meta">${esc(traffic.fastest_growing_project||'—')}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Traffic Quality</div><div class="activity-meta">${traffic.traffic_quality_score||0}/100</div></div></div>
  `);

  const rev = a.revenue_insights || {};
  set('analytics-syncer-revenue', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Total Tracked Revenue</div><div class="activity-meta">$${(rev.total_tracked_revenue_usd||0).toFixed(2)}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Primary Driver</div><div class="activity-meta">${esc(rev.primary_revenue_driver||'—')}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">RPM Benchmark</div><div class="activity-meta">$${(rev.rpm_benchmark||0).toFixed(2)}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Revenue Trend</div><div class="activity-meta" style="color:var(--${rev.revenue_trend==='growing'?'green':rev.revenue_trend==='declining'?'red':'yellow'})">${esc(rev.revenue_trend||'unknown')}</div></div></div>
  `);

  const optz = a.optimization_priorities || [];
  set('analytics-syncer-optz', optz.map(o =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--yellow)">→ ${esc(o)}</div></div></div>`
  ).join('') || '<div class="empty-state">No optimization priorities yet</div>');
}

function renderRevenueTracker(d) {
  const r = d.revenue_tracker || {};
  const portfolio = r.portfolio || {};
  const score = r.revenue_score || 0;
  const scoreColor = score >= 70 ? 'green' : score >= 40 ? 'yellow' : 'red';
  const totalMrr = portfolio.total_mrr_usd || 0;

  set('rev-tracker-cards', `
    <div class="card"><div class="card-label">Revenue Score</div><div class="card-value" style="color:var(--${scoreColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Total MRR</div><div class="card-value" style="color:var(--green)">$${totalMrr.toFixed(0)}</div></div>
    <div class="card"><div class="card-label">Target Attainment</div><div class="card-value" style="color:var(--${(portfolio.target_attainment_pct||0)>=80?'green':(portfolio.target_attainment_pct||0)>=50?'yellow':'red'})">${(portfolio.target_attainment_pct||0).toFixed(1)}%</div></div>
    <div class="card"><div class="card-label">Top Earner</div><div class="card-value" style="font-size:12px;color:var(--blue)">${esc(portfolio.highest_revenue_project||'—')}</div></div>
  `);

  const projects = r.projects || {};
  const yp = projects.yallaplays || {};
  set('rev-tracker-yallaplays', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Monthly Earnings</div><div class="activity-meta">$${(yp.estimated_monthly_earnings_usd||0).toFixed(2)} / target $${(yp.target_monthly_usd||5000).toLocaleString()}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">RPM</div><div class="activity-meta">$${(yp.rpm_usd||0).toFixed(2)} (target $2.50) · CTR ${((yp.ctr||0)*100).toFixed(2)}%</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Sessions</div><div class="activity-meta">${(yp.monthly_sessions||0).toLocaleString()} / month</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Data Source</div><div class="activity-meta" style="color:var(--${yp.data_source==='adsense_real'?'green':'yellow'})">${esc(yp.data_source||'estimated')}</div></div></div>
  `);

  const fio = projects.fionera || {};
  set('rev-tracker-fionera', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">MRR</div><div class="activity-meta">$${(fio.mrr_usd||0).toFixed(0)} / target $${(fio.target_mrr_usd||8000).toLocaleString()}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Paid Users</div><div class="activity-meta">${fio.paid_users||0} · ARPU $${(fio.arpu_usd||0).toFixed(2)}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Trial Conversion</div><div class="activity-meta">${((fio.trial_conversion_rate||0)*100).toFixed(1)}% (target 8%)</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">ARR</div><div class="activity-meta">$${(fio.arr_usd||0).toFixed(0)}</div></div></div>
  `);

  const mif = projects.mifteh || {};
  set('rev-tracker-mifteh', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">MRR</div><div class="activity-meta">$${(mif.estimated_mrr_usd||0).toFixed(0)} / target $${(mif.target_mrr_usd||15000).toLocaleString()}</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Leads / Month</div><div class="activity-meta">${mif.leads_per_month||0} leads · ${(mif.close_rate||0)*100}% close rate</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Active Clients</div><div class="activity-meta">${mif.estimated_clients||0} @ avg $${(mif.avg_deal_usd||0).toLocaleString()}/mo</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Pipeline</div><div class="activity-meta">$${(mif.pipeline_value_usd||0).toFixed(0)}</div></div></div>
  `);

  const actions = r.critical_revenue_actions || [];
  set('rev-tracker-actions', actions.slice(0,5).map(a =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--${a.priority==='immediate'?'red':a.priority==='this_week'?'yellow':'blue'})">${esc(a.action||'')}</div>
      <div class="activity-meta">[${esc(a.project||'')}] +$${(a.revenue_impact_usd||0).toFixed(0)} · ${esc(a.priority||'')}</div>
    </div></div>`
  ).join('') || `<div class="empty-state">${esc(r.highest_roi_action||'No actions yet')}</div>`);

  const history = r.recent_history || [];
  set('rev-tracker-history', history.slice(-7).reverse().map(h =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(h.date||'')}</span><span style="color:var(--green)">$${(h.total_mrr_usd||0).toFixed(0)}</span>
      </div>
      <div class="activity-meta">${(h.target_attainment_pct||0).toFixed(1)}% target</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No history yet — runs daily</div>');
}

function renderPageDeployer(d) {
  const pd = d.page_deployer || {};
  const score = pd.deployment_score || 0;
  const status = pd.cycle_status || 'unknown';
  const statusColor = status === 'healthy' ? 'green' : status === 'degraded' ? 'yellow' : 'red';

  set('page-deployer-cards', `
    <div class="card"><div class="card-label">Deploy Score</div><div class="card-value" style="color:var(--${statusColor})">${score}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Deployed (Cycle)</div><div class="card-value" style="color:var(--green)">${pd.cycle_deployed||0}</div></div>
    <div class="card"><div class="card-label">Queue Remaining</div><div class="card-value" style="color:var(--blue)">${pd.queue_remaining||0}</div></div>
    <div class="card"><div class="card-label">All-Time Deployed</div><div class="card-value" style="color:var(--blue)">${pd.total_deployed_all_time||0}</div></div>
  `);

  const deployed = pd.deployed_this_cycle || [];
  set('page-deployer-deployed', deployed.map(dep =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(dep.project)} — ${esc(dep.feature_type)}</span>
        <span style="color:var(--green)">${dep.files||0} files</span>
      </div>
      ${dep.pr_url ? `<div class="activity-meta"><a href="${esc(dep.pr_url)}" target="_blank" style="color:var(--blue)">View PR ↗</a></div>` : ''}
    </div></div>`
  ).join('') || '<div class="empty-state">No deployments this cycle</div>');

  const failed = pd.failed_this_cycle || [];
  set('page-deployer-queue', failed.map(f =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--red)">✗ ${esc(f.project)} — ${esc(f.feature_type)}</div>
      <div class="activity-meta">${esc(f.error||'')}</div>
    </div></div>`
  ).join('') || `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">Queue clear — ${pd.queue_remaining||0} batches pending</div><div class="activity-meta">Page deployer creates PRs — never auto-merges</div></div></div>`);

  set('page-deployer-safety', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ Auto-merge: NEVER</div><div class="activity-meta">All deployments require human PR review</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ Forbidden patterns checked</div><div class="activity-meta">No config, credentials, or infra files deployed</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ Rollback metadata included</div><div class="activity-meta">Every PR includes rollback instructions</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ Audit tracking active</div><div class="activity-meta">Deployment queue logged in memory/deployment_queue.json</div></div></div>
  `);

  const recs = pd.recommendations || [];
  set('page-deployer-recs', recs.map(r =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--yellow)">→ ${esc(r)}</div></div></div>`
  ).join('') || '<div class="empty-state">No recommendations yet</div>');
}

// ─── Phase M: Game Analytics ─────────────────────────────────────────────────

function renderTopGames(d) {
  const gf = d.game_factory || {};
  const gq = d.game_qa || {};
  const games = gf.games || [];
  const qaMap = {};
  for (const g of (gq.games||[])) qaMap[g.game_id] = g;

  const scored = games.map(g => ({
    ...g,
    qa_score: (qaMap[g.game_id]||{}).qa_score || g.qa_score || 0,
    grade: (qaMap[g.game_id]||{}).grade || g.grade || 'F',
  })).sort((a, b) => b.qa_score - a.qa_score);

  set('top-games-cards', `
    <div class="card"><div class="card-label">Total Games</div><div class="card-value" style="color:var(--blue)">${games.length}</div></div>
    <div class="card"><div class="card-label">Avg QA Score</div><div class="card-value" style="color:var(--yellow)">${gf.avg_qa_score||0}/100</div></div>
    <div class="card"><div class="card-label">QA Eligible</div><div class="card-value" style="color:var(--green)">${gf.total_eligible||0}</div></div>
    <div class="card"><div class="card-label">Pass Rate</div><div class="card-value" style="color:var(--blue)">${gf.pass_rate||'0%'}</div></div>
  `);

  set('top-games-list', scored.length ? `<div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#1e293b;color:var(--muted);text-align:left">
        <th style="padding:10px 12px">#</th>
        <th style="padding:10px 12px">Game</th>
        <th style="padding:10px 12px">Type</th>
        <th style="padding:10px 12px">QA</th>
        <th style="padding:10px 12px">Grade</th>
        <th style="padding:10px 12px">Status</th>
      </tr></thead>
      <tbody>${scored.map((g, i) => {
        const sc = (g.qa_score||0) >= 75 ? '#22c55e' : (g.qa_score||0) >= 50 ? '#eab308' : '#ef4444';
        return `<tr style="border-top:1px solid #1e293b">
          <td style="padding:8px 12px;color:var(--muted)">${i+1}</td>
          <td style="padding:8px 12px">${esc(g.name_en||g.game_id||'')}</td>
          <td style="padding:8px 12px;color:var(--blue)">${esc(g.game_type||'')}</td>
          <td style="padding:8px 12px;color:${sc};font-weight:600">${g.qa_score||0}/100</td>
          <td style="padding:8px 12px;color:${sc}">${esc(g.grade||'')}</td>
          <td style="padding:8px 12px">${g.qa_eligible?'<span style="color:#22c55e">✅</span>':'<span style="color:#ef4444">❌</span>'}</td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>` : '<div class="empty-state" style="padding:40px">No games yet — Game Factory runs at 02:00 UTC</div>');
}

function renderGameRevenue(d) {
  const pp = d.publishing_pipeline || {};
  const mon = pp.monetization || {};
  const config = mon.config || {};

  set('game-revenue-cards', `
    <div class="card"><div class="card-label">Deployed Games</div><div class="card-value" style="color:var(--blue)">${mon.deployed_games||0}</div></div>
    <div class="card"><div class="card-label">Est. Monthly Revenue</div><div class="card-value" style="color:var(--green)">$${(mon.est_monthly_revenue_usd||0).toFixed(2)}</div></div>
    <div class="card"><div class="card-label">Est. RPM</div><div class="card-value" style="color:var(--yellow)">${mon.est_rpm||'$0.00'}</div></div>
    <div class="card"><div class="card-label">Avg Session</div><div class="card-value" style="color:var(--blue)">${mon.est_session_min||0} min</div></div>
  `);

  set('game-revenue-config', [
    ['AdSense Zones', (config.adsense_placement_zones||[]).join(', ')],
    ['Target Session', `${config.target_session_duration_sec||0}s`],
    ['Replay Trigger', config.replay_trigger||'game_over'],
    ['Recommended Games', config.recommended_games_count||6],
    ['Sticky Mobile Ad', config.sticky_mobile_ad?'✅ Enabled':'❌ Disabled'],
    ['RPM Target', `$${config.min_rpm_target_usd||0} – $${config.max_rpm_target_usd||0}`],
  ].map(([k,v]) => `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(k)}<span style="float:right;color:var(--blue)">${esc(String(v))}</span></div></div></div>`).join('') || '<div class="empty-state">No config data</div>');

  set('game-revenue-estimates', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">💰 Monthly Revenue Estimate<span style="float:right">$${(mon.est_monthly_revenue_usd||0).toFixed(2)}</span></div><div class="activity-meta">Based on ${mon.deployed_games||0} deployed games × 500 sessions × ${mon.est_rpm||'$1.20'} RPM</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Annual Estimate<span style="float:right;color:var(--blue)">$${((mon.est_monthly_revenue_usd||0)*12).toFixed(2)}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--muted)">AdSense RPM target: ${config.min_rpm_target_usd||0} – ${config.max_rpm_target_usd||0} USD</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ Profitability-first execution mode active</div></div></div>
  `);
}

function renderCtrAnalytics(d) {
  const pp = d.publishing_pipeline || {};
  const games = pp.games || [];

  set('ctr-analytics-cards', `
    <div class="card"><div class="card-label">Games Tracked</div><div class="card-value" style="color:var(--blue)">${games.length}</div></div>
    <div class="card"><div class="card-label">SEO Velocity</div><div class="card-value" style="color:var(--yellow)">${esc(pp.seo_velocity||'normal').toUpperCase()}</div></div>
    <div class="card"><div class="card-label">Pipeline Health</div><div class="card-value" style="color:var(--${pp.pipeline_health==='healthy'?'green':pp.pipeline_health==='needs_attention'?'yellow':'red'})">${esc(pp.pipeline_health||'unknown').toUpperCase()}</div></div>
  `);

  set('ctr-analytics-games', games.map(g =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(g.name||g.game_id||'')}</span>
        <span style="color:var(--muted);font-size:11px">${g.completion_pct||0}% complete</span>
      </div>
      <div class="activity-meta">
        Type: ${esc(g.game_type||'')} · QA: ${g.qa_score||0}/100 · Status: ${esc(g.review_status||'')} · Steps: ${g.steps_done||0}/${g.steps_total||11}
        <div style="margin-top:4px;background:#1e293b;border-radius:4px;height:4px;overflow:hidden">
          <div style="background:${(g.completion_pct||0)>=75?'#22c55e':'#3b82f6'};width:${g.completion_pct||0}%;height:100%"></div>
        </div>
      </div>
    </div></div>`
  ).join('') || '<div class="empty-state">No pipeline data yet — run publishing pipeline workflow</div>');
}

function renderSeoRankings(d) {
  const gs = d.game_seo || {};
  const gf = d.game_factory || {};

  set('seo-rankings-cards', `
    <div class="card"><div class="card-label">SEO Pages</div><div class="card-value" style="color:var(--blue)">${gs.seo_pages_count||0}</div></div>
    <div class="card"><div class="card-label">Category Hubs</div><div class="card-value" style="color:var(--green)">${gs.category_hubs_count||0}</div></div>
    <div class="card"><div class="card-label">Keywords</div><div class="card-value" style="color:var(--yellow)">${(gs.total_keywords||0).toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Games w/ SEO</div><div class="card-value" style="color:var(--blue)">${gs.seo_pages_count||0}/${gf.total_generated||0}</div></div>
  `);

  set('seo-rankings-coverage', [
    ['SEO Pages Generated', gs.seo_pages_count||0],
    ['Category Hub Pages', gs.category_hubs_count||0],
    ['Total Arabic Keywords', (gs.total_keywords||0).toLocaleString()],
    ['SEO Engine Cost', `$${(gs.total_cost_usd||0).toFixed(4)}`],
  ].map(([k,v]) => `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(k)}<span style="float:right;color:var(--blue)">${esc(String(v))}</span></div></div></div>`).join('') || '<div class="empty-state">No SEO data yet</div>');

  const hubs = gs.hub_types || [];
  set('seo-rankings-keywords', hubs.length ? hubs.map(h =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(h)} <span style="color:var(--green)">✅ Hub Generated</span></div></div></div>`
  ).join('') : `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--muted)">Priority keywords: العاب سباق, العاب اطفال, العاب بازل, العاب اكشن, العاب سيارات</div></div></div>`);
}

function renderPublishingPipeline(d) {
  const pp = d.publishing_pipeline || {};
  const healthColor = pp.pipeline_health==='healthy'?'green':pp.pipeline_health==='needs_attention'?'yellow':'red';

  set('publishing-pipeline-cards', `
    <div class="card"><div class="card-label">Total Games</div><div class="card-value" style="color:var(--blue)">${pp.total_games||0}</div></div>
    <div class="card"><div class="card-label">Pending Approval</div><div class="card-value" style="color:var(--yellow)">${pp.pending_approval||0}</div></div>
    <div class="card"><div class="card-label">Approved</div><div class="card-value" style="color:var(--green)">${pp.approved||0}</div></div>
    <div class="card"><div class="card-label">Deployed</div><div class="card-value" style="color:var(--blue)">${pp.deployed||0}</div></div>
    <div class="card"><div class="card-label">Health</div><div class="card-value" style="color:var(--${healthColor})">${esc(pp.pipeline_health||'unknown').toUpperCase()}</div></div>
    <div class="card"><div class="card-label">Throughput</div><div class="card-value" style="color:var(--muted);font-size:14px">${esc(pp.throughput_estimate||'N/A')}</div></div>
  `);

  const steps = pp.step_summary || {};
  const STEP_ORDER = ['generate','qa_check','asset_gen','seo_page','internal_link','sitemap','approval','pr_created','deployed','indexed','tracking'];
  const STEP_LABELS = {generate:'🎮 Generate',qa_check:'✅ QA Check',asset_gen:'🖼 Assets',seo_page:'📄 SEO Page',internal_link:'🔗 Links',sitemap:'🗺 Sitemap',approval:'👤 Approval',pr_created:'📋 PR',deployed:'🚀 Deploy',indexed:'🔍 Index',tracking:'📊 Track'};

  set('publishing-pipeline-steps', STEP_ORDER.map(sid => {
    const s = steps[sid] || {};
    const pct = s.completion_pct || 0;
    const color = pct >= 75 ? '#22c55e' : pct >= 40 ? '#eab308' : '#ef4444';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(STEP_LABELS[sid]||sid)}</span>
        <span style="color:${color}">${s.done||0}/${s.total||0} (${pct}%)</span>
      </div>
      <div style="background:#1e293b;border-radius:4px;height:3px;margin-top:4px;overflow:hidden">
        <div style="background:${color};width:${pct}%;height:100%"></div>
      </div>
    </div></div>`;
  }).join('') || '<div class="empty-state">No pipeline steps tracked yet</div>');

  const games = (pp.games||[]).slice(0,10);
  set('publishing-pipeline-games', games.map(g =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(g.name||g.game_id)}</span>
        <span style="color:var(--muted)">${g.completion_pct||0}%</span>
      </div>
      <div class="activity-meta">${esc(g.game_type||'')} · ${esc(g.review_status||'')} · QA: ${g.qa_score||0}/100</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No games in pipeline</div>');

  const priorities = pp.top_priorities || [];
  set('publishing-pipeline-priorities', priorities.map(p =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--yellow)">→ ${esc(p)}</div></div></div>`
  ).join('') || `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--muted)">Bottleneck: ${esc(pp.bottleneck_step||'unknown')}</div></div></div>`);
}

function renderGameAssets(d) {
  const ga = d.game_assets || {};
  set('game-assets-cards', `
    <div class="card"><div class="card-label">Games w/ Assets</div><div class="card-value" style="color:var(--blue)">${ga.games_processed||0}</div></div>
    <div class="card"><div class="card-label">Category Banners</div><div class="card-value" style="color:var(--green)">${ga.categories_processed||0}</div></div>
    <div class="card"><div class="card-label">Total Assets</div><div class="card-value" style="color:var(--yellow)">${ga.total_assets_generated||0}</div></div>
  `);

  const assets = ga.game_assets || [];
  const banners = ga.category_banners || [];
  set('game-assets-list', assets.length ? `<div style="padding:16px">
    <div style="margin-bottom:12px;color:var(--muted);font-size:12px">GAME ASSETS (thumbnail + OG image + icon per game)</div>
    ${assets.map(a => `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(a.name_en||a.game_id)} <span style="color:var(--muted);font-size:11px">${esc(a.game_type||'')}</span></div>
      <div class="activity-meta">${(a.assets||[]).map(k=>`${esc(k)} ✅`).join(' · ')}</div>
    </div></div>`).join('')}
    ${banners.length ? `<div style="margin:16px 0 8px;color:var(--muted);font-size:12px">CATEGORY BANNERS (${banners.length} types)</div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">${banners.map(b=>esc(b)).join(', ')}</div></div></div>` : ''}
  </div>` : '<div class="empty-state" style="padding:40px">No assets generated yet — run ai-indexing-validation workflow</div>');
}

// ─── Phase M: Indexing ────────────────────────────────────────────────────────

function renderIndexingStatus(d) {
  const idx = d.indexing || {};
  const quotaUsed = idx.quota_used_today || 0;
  const quotaTotal = idx.daily_quota || 200;
  const quotaPct = Math.round(100 * quotaUsed / quotaTotal);
  const authColor = idx.credentials_configured ? 'green' : 'red';
  const srColor = (idx.success_rate||'N/A') === 'N/A' ? 'muted' : parseInt(idx.success_rate) >= 80 ? 'green' : 'yellow';

  set('indexing-status-cards', `
    <div class="card"><div class="card-label">Auth Mode</div><div class="card-value" style="color:var(--${authColor});font-size:14px">${esc(idx.auth_mode||'none').toUpperCase()}</div></div>
    <div class="card"><div class="card-label">Credentials</div><div class="card-value" style="color:var(--${authColor})">${idx.credentials_configured?'✅':'❌'}</div></div>
    <div class="card"><div class="card-label">Indexed Today</div><div class="card-value" style="color:var(--blue)">${quotaUsed}</div></div>
    <div class="card"><div class="card-label">Quota Remaining</div><div class="card-value" style="color:var(--green)">${idx.quota_remaining||quotaTotal}</div></div>
    <div class="card"><div class="card-label">Total Indexed</div><div class="card-value" style="color:var(--blue)">${idx.total_indexed_all_time||0}</div></div>
    <div class="card"><div class="card-label">Success Rate</div><div class="card-value" style="color:var(--${srColor})">${esc(idx.success_rate||'N/A')}</div></div>
  `);

  set('indexing-status-quota', `
    <div class="activity-item"><div class="activity-body">
      <div class="activity-title">Daily Quota Usage<span style="float:right;color:${quotaPct>80?'var(--red)':quotaPct>60?'var(--yellow)':'var(--green)'}">${quotaUsed}/${quotaTotal}</span></div>
      <div style="background:#1e293b;border-radius:4px;height:6px;margin-top:6px;overflow:hidden">
        <div style="background:${quotaPct>80?'#ef4444':quotaPct>60?'#eab308':'#22c55e'};width:${quotaPct}%;height:100%"></div>
      </div>
    </div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Queue Size<span style="float:right;color:var(--yellow)">${idx.queue_size||0} URLs</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Failed Submissions<span style="float:right;color:var(--red)">${idx.failed_count||0}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:${idx.credentials_configured?'var(--green)':'var(--red)'}">
      ${idx.credentials_configured?'✅ GOOGLE_SERVICE_ACCOUNT_JSON configured':'❌ Add GOOGLE_SERVICE_ACCOUNT_JSON to GitHub Secrets'}
    </div></div></div>
  `);

  const prio = idx.queue_by_priority || {};
  set('indexing-status-priority', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">High Priority<span style="float:right;color:var(--red)">${prio.high||0} URLs</span></div><div class="activity-meta">Newly deployed games</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Normal Priority<span style="float:right;color:var(--yellow)">${prio.normal||0} URLs</span></div><div class="activity-meta">SEO pages, category hubs</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Low Priority<span style="float:right;color:var(--muted)">${prio.low||0} URLs</span></div><div class="activity-meta">Supplementary pages</div></div></div>
  `);
}

function renderIndexingQueue(d) {
  const idx = d.indexing || {};
  const queue = idx.queue_preview || [];
  set('indexing-queue-cards', `
    <div class="card"><div class="card-label">Queue Size</div><div class="card-value" style="color:var(--yellow)">${idx.queue_size||0}</div></div>
    <div class="card"><div class="card-label">High Priority</div><div class="card-value" style="color:var(--red)">${(idx.queue_by_priority||{}).high||0}</div></div>
    <div class="card"><div class="card-label">Normal</div><div class="card-value" style="color:var(--yellow)">${(idx.queue_by_priority||{}).normal||0}</div></div>
  `);
  set('indexing-queue-list', queue.length ? queue.map(item =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span style="word-break:break-all;font-size:12px;color:var(--blue)">${esc((item.url||'').substring(0,80))}</span>
        <span style="color:${item.priority==='high'?'var(--red)':item.priority==='normal'?'var(--yellow)':'var(--muted)'};white-space:nowrap;margin-left:8px">${esc(item.priority||'normal')}</span>
      </div>
      <div class="activity-meta">Source: ${esc(item.source||'')} · Added: ${esc((item.added_at||'').substring(0,10))}</div>
    </div></div>`
  ).join('') : '<div class="empty-state" style="padding:40px">Queue empty — all URLs indexed or none queued yet</div>');
}

function renderIndexedUrls(d) {
  const idx = d.indexing || {};
  const urls = idx.recent_indexed || [];
  set('indexed-urls-cards', `
    <div class="card"><div class="card-label">Total Indexed</div><div class="card-value" style="color:var(--green)">${idx.total_indexed_all_time||0}</div></div>
    <div class="card"><div class="card-label">Indexed Today</div><div class="card-value" style="color:var(--blue)">${idx.indexed_today||0}</div></div>
    <div class="card"><div class="card-label">Success Rate</div><div class="card-value" style="color:var(--green)">${esc(idx.success_rate||'N/A')}</div></div>
  `);
  set('indexed-urls-list', urls.length ? urls.map(u =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--green)">✅ ${esc((u.url||'').substring(0,80))}</div>
      <div class="activity-meta">${esc((u.submitted_at||'').substring(0,16).replace('T',' '))} UTC · ${esc(u.notification_type||'URL_UPDATED')}</div>
    </div></div>`
  ).join('') : '<div class="empty-state" style="padding:40px">No URLs indexed yet — configure GOOGLE_SERVICE_ACCOUNT_JSON in GitHub Secrets</div>');
}

function renderFailedIndexing(d) {
  const idx = d.indexing || {};
  const failed = idx.recent_failed || [];
  set('failed-indexing-cards', `
    <div class="card"><div class="card-label">Failed URLs</div><div class="card-value" style="color:var(--red)">${idx.failed_count||0}</div></div>
    <div class="card"><div class="card-label">Retry Limit</div><div class="card-value" style="color:var(--muted)">3×</div></div>
  `);
  set('failed-indexing-list', failed.length ? failed.map(u =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--red)">❌ ${esc((u.url||'').substring(0,80))}</div>
      <div class="activity-meta">Error: ${esc(u.error||'')} · Retries: ${u.retry_count||0} · ${esc((u.submitted_at||'').substring(0,16).replace('T',' '))} UTC</div>
    </div></div>`
  ).join('') : '<div class="empty-state" style="padding:40px">No failed indexing submissions ✅</div>');
}

// ─── Phase L: Game Studio ─────────────────────────────────────────────────────

function renderGameFactory(d) {
  const gf = d.game_factory || {};
  const total = gf.total_generated || 0;
  const eligible = gf.total_eligible || 0;
  const passRate = gf.pass_rate || '0%';
  const avg = gf.avg_qa_score || 0;
  const cost = gf.total_cost_usd || 0;

  set('game-factory-cards', `
    <div class="card"><div class="card-label">Games Generated</div><div class="card-value" style="color:var(--blue)">${total}</div></div>
    <div class="card"><div class="card-label">QA Eligible</div><div class="card-value" style="color:var(--green)">${eligible}</div></div>
    <div class="card"><div class="card-label">Pass Rate</div><div class="card-value" style="color:var(--yellow)">${passRate}</div></div>
    <div class="card"><div class="card-label">Avg QA Score</div><div class="card-value" style="color:var(--blue)">${avg}<span style="font-size:14px;color:var(--muted)">/100</span></div></div>
    <div class="card"><div class="card-label">Total Cost</div><div class="card-value" style="color:var(--muted)">$${cost.toFixed(4)}</div></div>
  `);

  const games = gf.games || [];
  set('game-factory-games', games.map(g => {
    const scoreColor = (g.qa_score||0) >= 75 ? 'green' : (g.qa_score||0) >= 50 ? 'yellow' : 'red';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(g.name_en||g.game_id||'')}</span>
        <span style="color:var(--${scoreColor})">${g.qa_score||0}/100</span>
      </div>
      <div class="activity-meta">Type: ${esc(g.game_type||'')} · ID: ${esc(g.game_id||'')} · ${g.qa_eligible?'✅ Eligible':'❌ Not eligible'}</div>
    </div></div>`;
  }).join('') || '<div class="empty-state">No games generated yet — factory runs at 02:00 UTC</div>');

  const byType = gf.by_type || {};
  set('game-factory-types', Object.entries(byType).map(([t, c]) =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(t)}<span style="float:right;color:var(--blue)">${c} games</span></div></div></div>`
  ).join('') || '<div class="empty-state">No type data yet</div>');

  set('game-factory-cost', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Total Tokens<span style="float:right;color:var(--blue)">${(gf.total_tokens||0).toLocaleString()}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Total Cost<span style="float:right;color:var(--muted)">$${cost.toFixed(4)}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ No external images — Phaser Graphics API only</div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--green)">✅ Admin approval required before deploy</div></div></div>
  `);
}

function renderGeneratedGames(d) {
  const gf = d.game_factory || {};
  const games = gf.games || [];
  set('generated-games-list', games.length ? `
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#1e293b;color:var(--muted);text-align:left">
        <th style="padding:10px 12px">Game ID</th>
        <th style="padding:10px 12px">Name (EN)</th>
        <th style="padding:10px 12px">Type</th>
        <th style="padding:10px 12px">QA Score</th>
        <th style="padding:10px 12px">Status</th>
      </tr></thead>
      <tbody>
        ${games.map(g => {
          const scoreColor = (g.qa_score||0) >= 75 ? '#22c55e' : (g.qa_score||0) >= 50 ? '#eab308' : '#ef4444';
          return `<tr style="border-top:1px solid #1e293b">
            <td style="padding:8px 12px;font-family:monospace;font-size:11px;color:var(--muted)">${esc(g.game_id||'')}</td>
            <td style="padding:8px 12px">${esc(g.name_en||'')}</td>
            <td style="padding:8px 12px;color:var(--blue)">${esc(g.game_type||'')}</td>
            <td style="padding:8px 12px;color:${scoreColor};font-weight:600">${g.qa_score||0}/100</td>
            <td style="padding:8px 12px">${g.qa_eligible ? '<span style="color:#22c55e">✅ Eligible</span>' : '<span style="color:#ef4444">❌ Below 75</span>'}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table></div>
  ` : '<div class="empty-state" style="padding:40px">No games generated yet. Game Factory runs at 02:00 UTC daily.</div>');
}

function renderGameQA(d) {
  const gq = d.game_qa || {};
  const summary = gq.summary || {};
  const games = gq.games || [];

  set('game-qa-cards', `
    <div class="card"><div class="card-label">Total Checked</div><div class="card-value" style="color:var(--blue)">${summary.total_games||0}</div></div>
    <div class="card"><div class="card-label">Eligible</div><div class="card-value" style="color:var(--green)">${summary.eligible_for_deploy||0}</div></div>
    <div class="card"><div class="card-label">Failed QA</div><div class="card-value" style="color:var(--red)">${summary.failed_qa||0}</div></div>
    <div class="card"><div class="card-label">Avg Score</div><div class="card-value" style="color:var(--yellow)">${summary.avg_score||0}</div></div>
    <div class="card"><div class="card-label">Pass Rate</div><div class="card-value" style="color:var(--blue)">${summary.pass_rate||'0%'}</div></div>
  `);

  const passed = games.filter(g => g.eligible);
  const failed = games.filter(g => !g.eligible);

  set('game-qa-results', passed.map(g =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span style="color:var(--green)">✅ ${esc(g.game_name||g.game_id)}</span>
        <span style="color:var(--green)">${g.qa_score}/100 (${esc(g.grade||'')})</span>
      </div>
      <div class="activity-meta">Game ID: ${esc(g.game_id||'')} · ${g.html_size_bytes ? Math.round(g.html_size_bytes/1024)+'KB' : ''}</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No games passed QA yet</div>');

  set('game-qa-failed', failed.map(g =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span style="color:var(--red)">❌ ${esc(g.game_name||g.game_id)}</span>
        <span style="color:var(--red)">${g.qa_score}/100</span>
      </div>
      <div class="activity-meta">${esc((g.issues||[]).slice(0,3).join(' · '))}</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No QA failures</div>');
}

function renderGameSeo(d) {
  const gs = d.game_seo || {};
  set('game-seo-cards', `
    <div class="card"><div class="card-label">SEO Pages</div><div class="card-value" style="color:var(--blue)">${gs.seo_pages_count||0}</div></div>
    <div class="card"><div class="card-label">Category Hubs</div><div class="card-value" style="color:var(--green)">${gs.category_hubs_count||0}</div></div>
    <div class="card"><div class="card-label">Total Keywords</div><div class="card-value" style="color:var(--yellow)">${(gs.total_keywords||0).toLocaleString()}</div></div>
    <div class="card"><div class="card-label">Cost</div><div class="card-value" style="color:var(--muted)">$${(gs.total_cost_usd||0).toFixed(4)}</div></div>
  `);

  const topGames = gs.top_games || [];
  set('game-seo-pages', topGames.map(g =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(g.name_en||g.game_id||'')}</div>
      <div class="activity-meta">${esc(g.keywords_count||0)} keywords · ${esc(g.has_faq?'FAQ ✅':'No FAQ')}</div>
    </div></div>`
  ).join('') || '<div class="empty-state">Run game-seo workflow to generate SEO pages</div>');

  const hubs = gs.hub_types || [];
  set('game-seo-hubs', hubs.length ? hubs.map(h =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title">${esc(h)}</div></div></div>`
  ).join('') : '<div class="empty-state">No category hubs generated yet</div>');
}

// ─── Phase L: Admin & Governance ─────────────────────────────────────────────

function renderAdminCenter(d) {
  const ag = d.admin_governance || {};
  const counts = ag.counts || {};
  const aiSummary = ag.ai_summary || {};
  const health = aiSummary.health_status || 'unknown';
  const healthColor = health === 'healthy' ? 'green' : health === 'needs_attention' ? 'yellow' : 'red';

  set('admin-center-cards', `
    <div class="card"><div class="card-label">Total Reviews</div><div class="card-value" style="color:var(--blue)">${counts.total||0}</div></div>
    <div class="card"><div class="card-label">Pending</div><div class="card-value" style="color:var(--yellow)">${counts.pending||0}</div></div>
    <div class="card"><div class="card-label">QA Eligible</div><div class="card-value" style="color:var(--green)">${counts.qa_eligible||0}</div></div>
    <div class="card"><div class="card-label">Approved</div><div class="card-value" style="color:var(--green)">${counts.approved||0}</div></div>
    <div class="card"><div class="card-label">Deployed</div><div class="card-value" style="color:var(--blue)">${counts.deployed||0}</div></div>
    <div class="card"><div class="card-label">Backlog Risk</div><div class="card-value" style="color:var(--${healthColor})">${esc(aiSummary.backlog_risk||'unknown').toUpperCase()}</div></div>
  `);

  set('admin-center-queue', `
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Health Status<span style="float:right;color:var(--${healthColor})">${esc(health).toUpperCase()}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Pending Review<span style="float:right;color:var(--yellow)">${counts.pending||0}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Approved (awaiting deploy)<span style="float:right;color:var(--green)">${counts.approved||0}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Deployed<span style="float:right;color:var(--blue)">${counts.deployed||0}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Rejected<span style="float:right;color:var(--red)">${counts.rejected||0}</span></div></div></div>
    <div class="activity-item"><div class="activity-body"><div class="activity-title">Rolled Back<span style="float:right;color:var(--red)">${counts.rolled_back||0}</span></div></div></div>
  `);

  const recs = aiSummary.recommendations || [];
  const actions = aiSummary.action_items || [];
  set('admin-center-ai', [...recs, ...actions].map(r =>
    `<div class="activity-item"><div class="activity-body"><div class="activity-title" style="color:var(--yellow)">→ ${esc(r)}</div></div></div>`
  ).join('') || '<div class="empty-state">No AI recommendations yet</div>');

  const audit = ag.recent_audit || [];
  set('admin-center-audit', audit.slice().reverse().map(a =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(a.action||'')} — ${esc(a.item_id||'')} <span style="float:right;color:var(--muted);font-size:11px">${esc((a.timestamp||'').substring(11,16))} UTC</span></div>
      <div class="activity-meta">${esc(a.detail||'')} (by ${esc(a.actor||'')})</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No audit events yet</div>');
}

function renderReviewQueue(d) {
  const ag = d.admin_governance || {};
  const counts = ag.counts || {};

  set('review-queue-cards', `
    <div class="card"><div class="card-label">Pending</div><div class="card-value" style="color:var(--yellow)">${counts.pending||0}</div></div>
    <div class="card"><div class="card-label">QA Eligible</div><div class="card-value" style="color:var(--green)">${counts.qa_eligible||0}</div></div>
    <div class="card"><div class="card-label">Approved</div><div class="card-value" style="color:var(--green)">${counts.approved||0}</div></div>
    <div class="card"><div class="card-label">Rejected</div><div class="card-value" style="color:var(--red)">${counts.rejected||0}</div></div>
  `);

  const renderItems = (items, emptyMsg) => (items||[]).map(r =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span>${esc(r.name||r.review_id||'')}</span>
        <span style="color:${(r.qa_score||0)>=75?'var(--green)':'var(--red)'}">${r.qa_score||0}/100</span>
      </div>
      <div class="activity-meta">ID: ${esc(r.review_id||'')} · Type: ${esc(r.game_type||r.type||'')} · ${esc(r.status||'')}</div>
    </div></div>`
  ).join('') || `<div class="empty-state">${emptyMsg}</div>`;

  set('review-queue-pending', renderItems(ag.pending, 'No pending reviews'));
  set('review-queue-eligible', renderItems(ag.qa_eligible, 'No QA-eligible games waiting'));
  set('review-queue-approved', renderItems(ag.approved, 'No approved games yet'));
  set('review-queue-rejected', renderItems(ag.rejected, 'No rejections'));
}

function renderDeployCenter(d) {
  const ag = d.admin_governance || {};
  const counts = ag.counts || {};

  set('deploy-center-cards', `
    <div class="card"><div class="card-label">Deployed</div><div class="card-value" style="color:var(--blue)">${counts.deployed||0}</div></div>
    <div class="card"><div class="card-label">Rolled Back</div><div class="card-value" style="color:var(--red)">${counts.rolled_back||0}</div></div>
    <div class="card"><div class="card-label">Approved (Ready)</div><div class="card-value" style="color:var(--green)">${counts.approved||0}</div></div>
  `);

  set('deploy-center-deployed', (ag.deployed||[]).map(r =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--green)">✅ ${esc(r.name||r.review_id||'')} — ${esc(r.game_type||'')}</div>
      ${r.pr_url ? `<div class="activity-meta"><a href="${esc(r.pr_url)}" target="_blank" style="color:var(--blue)">View PR ↗</a></div>` : ''}
    </div></div>`
  ).join('') || '<div class="empty-state">No deployed games yet — admin approval required first</div>');

  set('deploy-center-rollbacks', (ag.rolled_back||[]).map(r =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--red)">↩ ${esc(r.name||r.review_id||'')} rolled back</div>
      <div class="activity-meta">${esc(r.review_id||'')}</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No rollbacks</div>');
}

function renderDeployTimeline(d) {
  const ag = d.admin_governance || {};
  const audit = ag.recent_audit || [];
  set('deploy-timeline-audit', audit.length ? `
    <div style="padding:16px">
      ${audit.slice().reverse().map(a => {
        const color = a.action === 'deploy' ? 'var(--green)' : a.action === 'approve' ? 'var(--blue)' : a.action === 'reject' ? 'var(--red)' : a.action === 'rollback' ? 'var(--red)' : 'var(--muted)';
        return `<div class="activity-item"><div class="activity-body">
          <div class="activity-title" style="color:${color}">${esc(a.action||'').toUpperCase()} — ${esc(a.item_id||'')} <span style="float:right;font-size:11px;color:var(--muted)">${esc((a.timestamp||'').substring(0,16).replace('T',' '))} UTC</span></div>
          <div class="activity-meta">${esc(a.detail||'')} (${esc(a.actor||'')})</div>
        </div></div>`;
      }).join('')}
    </div>
  ` : '<div class="empty-state" style="padding:40px">No audit events yet — actions are logged here when admin approves/rejects/deploys games</div>');
}

function renderTelegramLogs(d) {
  const tl = d.telegram_logs || {};
  const entries = tl.entries || [];
  const total = tl.total_sent || 0;

  set('telegram-logs-cards', `
    <div class="card"><div class="card-label">Total Sent</div><div class="card-value" style="color:var(--blue)">${total}</div></div>
    <div class="card"><div class="card-label">Log Entries</div><div class="card-value" style="color:var(--green)">${entries.length}</div></div>
  `);

  const priorityColor = {info:'var(--muted)',success:'var(--green)',warning:'var(--yellow)',error:'var(--red)',critical:'var(--red)'};
  set('telegram-logs-entries', entries.slice().reverse().map(e =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="display:flex;justify-content:space-between">
        <span style="color:${priorityColor[e.priority]||'var(--muted)'}">${esc(e.event_type||'')}</span>
        <span style="color:var(--muted);font-size:11px">${esc((e.timestamp||'').substring(11,16))} UTC</span>
      </div>
      <div class="activity-meta">${esc(e.message||'')}</div>
    </div></div>`
  ).join('') || '<div class="empty-state">No Telegram messages logged yet — configure TELEGRAM_LOG_TOKEN secret</div>');
}

function renderLiveAlerts(d) {
  const ag = d.admin_governance || {};
  const aiSummary = ag.ai_summary || {};
  const tl = d.telegram_logs || {};
  const entries = (tl.entries || []).filter(e => ['warning','error','critical'].includes(e.priority));
  const gq = d.game_qa || {};
  const qaFailed = (gq.games||[]).filter(g => !g.eligible);

  const alerts = [];
  if ((ag.counts||{}).pending > 5) alerts.push({level:'warning',msg:`${ag.counts.pending} games pending admin review`});
  if (aiSummary.health_status === 'critical') alerts.push({level:'critical',msg:'Admin governance health: CRITICAL'});
  if (aiSummary.backlog_risk === 'high') alerts.push({level:'warning',msg:'Review backlog risk is HIGH'});
  qaFailed.slice(0,3).forEach(g => alerts.push({level:'warning',msg:`QA failed: ${g.game_name||g.game_id} — ${g.qa_score}/100`}));
  entries.slice(0,5).forEach(e => alerts.push({level:e.priority,msg:e.message||''}));

  const colorMap = {warning:'var(--yellow)',error:'var(--red)',critical:'var(--red)',info:'var(--blue)'};
  set('live-alerts-list', alerts.length ? `<div style="padding:16px">` + alerts.map(a =>
    `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:${colorMap[a.level]||'var(--muted)'}">
        ${a.level==='critical'?'🚨':a.level==='error'?'🔴':a.level==='warning'?'⚠️':'ℹ️'} ${esc(a.msg)}
      </div>
    </div></div>`
  ).join('') + `</div>` : `<div class="empty-state" style="padding:40px">✅ No active alerts — system operating normally</div>`);
}

// ─── Phase N.2: Focus Mode & Target Tracker ───────────────────────────────────

function renderTargetTracker(d) {
  const tt = d.target_tracker || {};
  const fm = d.focus_mode || {};
  const checks = tt.checks || [];
  const history = tt.history || [];
  const met = tt.targets_met || 0;
  const total = tt.targets_total || 0;
  const allMet = tt.all_targets_met;
  const learning = d.learning_insights || {};
  const trends = learning.trends || [];

  set('target-tracker-cards', [
    card('Targets Met Today', `${met}/${total}`, allMet ? '✅' : '🎯'),
    card('Status', tt.health || 'unknown', tt.health === 'healthy' ? '🟢' : tt.health === 'critical' ? '🔴' : '🟡'),
    card('Focus Mode', fm.label ? fm.label.replace('YallaPlays ','') : 'Active', '📌'),
    card('Expires', fm.expires_at ? fm.expires_at.slice(0, 10) : '—', '⏱'),
    card('Allocation', fm.allocation ? `${fm.allocation.yallaplays || 80}% YP` : '80% YP', '⬡'),
    card('Trends Detected', trends.length, '📈'),
  ].join(''));

  const checkRows = checks.length ? checks.map(c => {
    const icon = c.met ? '✅' : '❌';
    const gap = c.gap > 0 ? `<span style="color:var(--red);font-size:11px"> (gap: ${c.gap})</span>` : '';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${icon} ${esc(c.label)}</div>
      <div class="activity-meta">Actual: <b>${c.actual}</b> / Target: ${c.target}${gap}</div>
    </div></div>`;
  }).join('') : `<div class="empty-state" style="padding:40px">🎯 Target data available after first runtime run<br><span style="color:var(--muted);font-size:12px">Orchestrator runs every 4 hours</span></div>`;

  set('target-tracker-checks', `<div style="padding:8px">${checkRows}</div>`);

  const histRows = history.length ? history.slice().reverse().map(h => {
    const icon = h.all_met ? '✅' : '⚠️';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${icon} ${esc(h.date)}</div>
      <div class="activity-meta">Games: ${h.games} · SEO: ${h.seo_pages} · QA: ${h.qa_avg}/100 · Targets: ${h.targets_met}/${h.targets_total}</div>
    </div></div>`;
  }).join('') : `<div class="empty-state" style="padding:40px">📅 History builds over 7 days</div>`;

  set('target-tracker-history', `<div style="padding:8px">${histRows}</div>`);
}

// ─── Phase N: Runtime OS ──────────────────────────────────────────────────────

function renderRuntimeHealth(d) {
  const rw = d.runtime_workers || {};
  const systemHealth = rw.system_health || 'UNKNOWN';
  const healthColor = {HEALTHY:'var(--green)',WARNING:'var(--yellow)',DEGRADED:'var(--orange,#f97316)',CRITICAL:'var(--red)',RECOVERING:'var(--blue)',UNKNOWN:'var(--muted)'}[systemHealth] || 'var(--muted)';
  const workers = rw.workers || {};
  const issues = rw.all_issues || [];
  const issueCounts = rw.issue_counts || {};

  set('runtime-health-cards', [
    card('System Health', `<span style="color:${healthColor};font-size:24px;font-weight:700">${systemHealth}</span>`, '⬡'),
    card('Total Issues', rw.total_issues || 0, '⚠️'),
    card('Critical', issueCounts.critical || 0, '🔴'),
    card('Warning', issueCounts.warning || 0, '🟡'),
    card('Last Heartbeat', rw.last_heartbeat ? rw.last_heartbeat.replace('T',' ').replace('Z','') : 'Never', '💓'),
    card('Runtime Status', rw.runtime_status || 'unknown', '⚙'),
  ].join(''));

  const workerRows = Object.entries(workers).map(([name, w]) => {
    const hc = {healthy:'var(--green)',warning:'var(--yellow)',degraded:'var(--orange,#f97316)',critical:'var(--red)',error:'var(--red)',not_run:'var(--muted)',unknown:'var(--muted)'}[w.health] || 'var(--muted)';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${esc(name.replace(/_/g,' '))}</div>
      <div class="activity-meta">Health: <span style="color:${hc}">${esc(w.health)}</span> · Issues: ${w.issue_count||0} · ${w.timestamp?w.timestamp.replace('T',' ').replace('Z',''):'Never run'}</div>
    </div></div>`;
  }).join('') || `<div class="empty-state" style="padding:40px">⚙️ Runtime workers not yet executed — runtime orchestrator will run on schedule</div>`;

  set('runtime-health-workers', `<div style="padding:8px">${workerRows}</div>`);

  const issueRows = issues.length ? issues.map(i => {
    const sev = i.severity || 'info';
    const emoji = sev==='critical'?'🔴':sev==='warning'?'🟡':'ℹ️';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${emoji} ${esc(i.detail||'')}</div>
      <div class="activity-meta">${esc(i.worker||'')} · ${esc(i.type||'')}</div>
    </div></div>`;
  }).join('') : `<div class="empty-state" style="padding:40px">✅ No open issues</div>`;

  set('runtime-health-issues', `<div style="padding:8px">${issueRows}</div>`);
}

function renderRuntimeWorkers(d) {
  const rw = d.runtime_workers || {};
  const workers = rw.workers || {};
  const ok = rw.scheduler_ok || 0;
  const errors = rw.scheduler_errors || 0;
  const elapsed = rw.scheduler_elapsed_sec || 0;

  set('runtime-workers-cards', [
    card('Workers OK', ok, '✅'),
    card('Workers Failed', errors, '❌'),
    card('Elapsed', elapsed ? `${elapsed}s` : '—', '⏱'),
    card('Total Workers', Object.keys(workers).length, '⚙'),
  ].join(''));

  const rows = Object.entries(workers).map(([name, w]) => {
    const hc = {healthy:'var(--green)',warning:'var(--yellow)',degraded:'var(--orange,#f97316)',critical:'var(--red)',error:'var(--red)',not_run:'var(--muted)',unknown:'var(--muted)'}[w.health]||'var(--muted)';
    const ts = w.timestamp ? w.timestamp.replace('T',' ').replace('Z','') : 'Never run';
    return `<tr>
      <td style="padding:8px;border-bottom:1px solid var(--border)">${esc(name.replace(/_/g,' '))}</td>
      <td style="padding:8px;border-bottom:1px solid var(--border);color:${hc}">${esc(w.health)}</td>
      <td style="padding:8px;border-bottom:1px solid var(--border);color:var(--muted)">${esc(w.status)}</td>
      <td style="padding:8px;border-bottom:1px solid var(--border);color:var(--muted);font-size:11px">${ts}</td>
      <td style="padding:8px;border-bottom:1px solid var(--border);text-align:center">${w.issue_count||0}</td>
    </tr>`;
  }).join('');

  set('runtime-workers-manifest', `<div style="padding:8px;overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="color:var(--muted);font-size:11px">
        <th style="padding:8px;text-align:left">Worker</th>
        <th style="padding:8px;text-align:left">Health</th>
        <th style="padding:8px;text-align:left">Status</th>
        <th style="padding:8px;text-align:left">Last Run</th>
        <th style="padding:8px;text-align:center">Issues</th>
      </tr></thead>
      <tbody>${rows || '<tr><td colspan="5" style="padding:24px;text-align:center;color:var(--muted)">No worker data yet — orchestrator runs every 4 hours</td></tr>'}</tbody>
    </table>
  </div>`);
}

function renderRuntimeProviders(d) {
  const rw = d.runtime_workers || {};
  const ph = (d.providers || {});
  const oaStatus = rw.provider_openai || ph.openai?.status || 'unknown';
  const gmStatus = rw.provider_gemini || ph.gemini?.status || 'unknown';

  const statusColor = s => ({healthy:'var(--green)',degraded:'var(--yellow)',critical:'var(--red)',unknown:'var(--muted)'}[s]||'var(--muted)');

  set('runtime-providers-cards', [
    card('OpenAI', `<span style="color:${statusColor(oaStatus)}">${oaStatus.toUpperCase()}</span>`, '⚡'),
    card('Gemini', `<span style="color:${statusColor(gmStatus)}">${gmStatus.toUpperCase()}</span>`, '⚡'),
    card('Failover', 'OpenAI → Gemini', '↺'),
    card('Mode', ph.ai_mode || 'ai', '⚙'),
  ].join(''));

  set('runtime-providers-detail', `<div style="padding:16px">
    <div style="margin-bottom:12px;padding:12px;background:var(--surface2);border-radius:8px">
      <div style="font-weight:600;margin-bottom:4px">⚡ OpenAI (gpt-4o-mini)</div>
      <div style="color:${statusColor(oaStatus)};font-size:13px">Status: ${oaStatus}</div>
      <div style="color:var(--muted);font-size:12px;margin-top:4px">Primary provider · $0.15/1M input · $0.60/1M output</div>
    </div>
    <div style="padding:12px;background:var(--surface2);border-radius:8px">
      <div style="font-weight:600;margin-bottom:4px">⚡ Gemini (gemini-1.5-flash)</div>
      <div style="color:${statusColor(gmStatus)};font-size:13px">Status: ${gmStatus}</div>
      <div style="color:var(--muted);font-size:12px;margin-top:4px">Fallback provider · $0.075/1M input · $0.30/1M output · Set GEMINI_API_KEY secret to activate</div>
    </div>
  </div>`);
}

function renderRuntimeReports(d) {
  const rw = d.runtime_workers || {};
  set('runtime-reports-cards', [
    card('Daily Reports', 'memory/daily_reports/', '📋'),
    card('Weekly Reports', 'memory/weekly_reports/', '📊'),
    card('Schedule', '06:00 UTC daily · 07:00 UTC Sunday', '🕐'),
    card('Heartbeat', rw.last_heartbeat ? rw.last_heartbeat.replace('T',' ').replace('Z','') : 'Never', '💓'),
  ].join(''));

  set('runtime-reports-list', `<div style="padding:16px">
    <div style="margin-bottom:12px">
      <div style="font-weight:600;margin-bottom:8px">📋 Daily Reports</div>
      <div style="color:var(--muted);font-size:13px">Sent daily at 09:00 Istanbul (06:00 UTC) via Telegram.<br>
      Covers: system health, games, SEO, indexing, revenue, providers, open issues.<br>
      Stored in: memory/daily_reports/</div>
    </div>
    <div style="margin-bottom:12px">
      <div style="font-weight:600;margin-bottom:8px">📊 Weekly Reports</div>
      <div style="color:var(--muted);font-size:13px">Sent Sunday at 10:00 Istanbul (07:00 UTC) via Telegram.<br>
      Covers: week-over-week deltas, revenue progress, AI provider uptime, all worker metrics.<br>
      Stored in: memory/weekly_reports/</div>
    </div>
    <div>
      <div style="font-weight:600;margin-bottom:8px">⚙️ Runtime Orchestrator</div>
      <div style="color:var(--muted);font-size:13px">Runs every 4 hours. Executes all 9 workers in sequence.<br>
      Sends Telegram alert only on DEGRADED or CRITICAL health.<br>
      Stores heartbeat in: memory/runtime_heartbeat.json</div>
    </div>
  </div>`);
}

function renderRuntimeIncidents(d) {
  const rw = d.runtime_workers || {};
  const issues = rw.all_issues || [];
  const issueCounts = rw.issue_counts || {};

  set('runtime-incidents-cards', [
    card('Total Issues', rw.total_issues || 0, '⚠️'),
    card('Critical', issueCounts.critical || 0, '🔴'),
    card('Warning', issueCounts.warning || 0, '🟡'),
    card('Info', issueCounts.info || 0, 'ℹ️'),
  ].join(''));

  const rows = issues.length ? issues.map(i => {
    const sev = i.severity || 'info';
    const emoji = sev==='critical'?'🔴':sev==='warning'?'🟡':'ℹ️';
    return `<div class="activity-item"><div class="activity-body">
      <div class="activity-title">${emoji} ${esc(i.detail||'')}</div>
      <div class="activity-meta">${esc(i.worker||'')} · ${esc(i.type||'')} · ${esc(sev)}</div>
    </div></div>`;
  }).join('') : `<div class="empty-state" style="padding:40px">✅ No incidents — system operating normally<br><span style="color:var(--muted);font-size:12px">Incidents from AI provider failures are stored in memory/incidents/</span></div>`;

  set('runtime-incidents-list', `<div style="padding:8px">${rows}</div>`);
}

// ─── Actions (GitHub-native) ─────────────────────────────────────────────────

function triggerLoop(loopId) {
  // In GitHub-native mode, redirect to GitHub Actions for manual dispatch
  const url = _ACTIONS.dashboard || 'https://github.com/Zakoosh/MIFTEH-AI-OS/actions';
  window.open(url, '_blank');
}

function createPR(project) {
  window.open(_ACTIONS.prs || 'https://github.com/Zakoosh/MIFTEH-AI-OS/actions/workflows/ai-pr-generator.yml', '_blank');
  const resultEl = document.getElementById('pr-create-result');
  if (resultEl) resultEl.innerHTML = `<div style="padding:10px;background:#052e16;border:1px solid #166534;border-radius:6px;font-size:12px;">
    ✅ <strong>Opened GitHub Actions</strong><br>
    <span style="color:var(--dim);">Click "Run workflow" to create a draft PR for ${esc(project)}</span>
  </div>`;
}

function createPRFromOutput() {
  window.open(_ACTIONS.prs || 'https://github.com/Zakoosh/MIFTEH-AI-OS/actions/workflows/ai-pr-generator.yml', '_blank');
}

// ─── Load ────────────────────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    // Cache-bust with timestamp so we always get the latest generated JSON
    const url = _DATA_URL + '?t=' + Math.floor(Date.now() / 30000);
    const resp = await fetch(url, { cache: 'no-store' });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    _data = await resp.json();

    const sched = (_data.scheduler || {});
    const dot = document.getElementById('system-dot');
    const txt = document.getElementById('system-status-text');
    if (dot) { dot.style.background = '#22c55e'; dot.style.boxShadow = '0 0 6px #22c55e'; }
    if (txt) txt.textContent = 'SYSTEM ONLINE';

    const lu = document.getElementById('last-updated');
    if (lu) lu.textContent = 'Updated ' + new Date().toLocaleTimeString();

    const meta = document.getElementById('page-meta');
    if (meta) {
      const ai = _data.ai_analytics || {};
      meta.textContent = `${(_data.outputs || {}).total || 0} outputs · ${sched.active_loops || 0}/${sched.total_loops || 14} loops · $${(ai.total_cost_usd || 0).toFixed(4)} AI cost · GitHub-native`;
    }

    renderOverview(_data);
    renderLoops(_data);
    renderProviders(_data);
    renderAIAnalytics(_data);
    renderOutputs(_data);
    renderPreviews(_data);
    renderRepository(_data);
    renderGitHub(_data);
    renderAnalytics(_data);
    renderProduct(_data);
    renderTrust(_data);
    renderHealth(_data);
    renderRoadmap(_data);
    renderExecutor(_data);
    renderAIQA(_data);
    renderBrowser(_data);
    renderMonitor(_data);
    renderMemory(_data);
    renderRevenue(_data);
    renderSwarm(_data);
    renderStrategy(_data);
    renderMarket(_data);
    renderPriority(_data);
    renderExperiments(_data);
    renderCrossLearn(_data);
    renderEvolution(_data);
    renderWebIntel(_data);
    renderSeoOpportunities(_data);
    renderCompetitorMemory(_data);
    renderSocialSignals(_data);
    renderTrafficIntel(_data);
    renderMonetization(_data);
    renderCampaigns(_data);
    renderRealtimeAlerts(_data);
    renderKnowledgeGraph(_data);
    renderAgents(_data);
    renderCognition(_data);
    renderGovernance(_data);
    renderEconomy(_data);
    renderKernel(_data);
    renderCivilization(_data);
    renderGrowth(_data);
    renderRevenue(_data);
    renderConversions(_data);
    renderAcquisition(_data);
    renderScaling(_data);
    renderDeployments(_data);
    renderVecMem(_data);
    renderRetrieval(_data);
    renderToolRuntime(_data);
    renderResearch(_data);
    renderSandbox(_data);
    renderObservability(_data);
    renderKpiTracker(_data);
    renderRoiAgent(_data);
    renderProgSeo(_data);
    renderProductBuilder(_data);
    renderClientAcquisition(_data);
    renderAnalyticsSyncer(_data);
    renderRevenueTracker(_data);
    renderPageDeployer(_data);
    renderTopGames(_data);
    renderGameRevenue(_data);
    renderCtrAnalytics(_data);
    renderSeoRankings(_data);
    renderPublishingPipeline(_data);
    renderGameAssets(_data);
    renderIndexingStatus(_data);
    renderIndexingQueue(_data);
    renderIndexedUrls(_data);
    renderFailedIndexing(_data);
    renderGameFactory(_data);
    renderGeneratedGames(_data);
    renderGameQA(_data);
    renderGameSeo(_data);
    renderAdminCenter(_data);
    renderReviewQueue(_data);
    renderDeployCenter(_data);
    renderDeployTimeline(_data);
    renderTelegramLogs(_data);
    renderLiveAlerts(_data);
    renderTargetTracker(_data);
    renderRuntimeHealth(_data);
    renderRuntimeWorkers(_data);
    renderRuntimeProviders(_data);
    renderRuntimeReports(_data);
    renderRuntimeIncidents(_data);
    renderActivity(_data);
    renderSafety(_data);
    renderFocusBanner(_data);
    autoHideEmptySections();

  } catch (err) {
    console.error('Dashboard load error:', err);
    const dot = document.getElementById('system-dot');
    const txt = document.getElementById('system-status-text');
    if (dot) { dot.style.background = '#eab308'; dot.style.boxShadow = ''; }
    if (txt) txt.textContent = 'DATA LOADING';
    set('activity-mini', `<div class="activity-item"><div class="activity-body">
      <div class="activity-title" style="color:var(--yellow);">Waiting for first AI workflow run</div>
      <div class="activity-meta">${esc(err.message)} — workflows run on cron schedule</div>
    </div></div>`);
  }
}

(async () => {
  // Ctrl+K command palette
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const palette = document.getElementById('command-palette');
      if (palette && palette.style.display === 'block') {
        closeCommandPalette();
      } else {
        openCommandPalette();
      }
    }
    if (e.key === 'Escape') closeCommandPalette();
  });

  const ok = await initAuth();
  if (ok) {
    loadDashboard();
    setInterval(loadDashboard, 60000);
  }
})();
