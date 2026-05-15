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
    renderActivity(_data);
    renderSafety(_data);

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
  const ok = await initAuth();
  if (ok) {
    loadDashboard();
    setInterval(loadDashboard, 60000);
  }
})();
