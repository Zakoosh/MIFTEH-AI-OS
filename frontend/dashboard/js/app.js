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

function renderPreviews(d) {
  const previews = (d.repository || {}).previews || [];
  set('previews-badge', `<span class="panel-badge badge-dim">${previews.length} files</span>`);
  set('previews-list', previews.length ? previews.map(p => `
    <div class="output-row"><span class="output-type-tag">HTML</span>
    <span class="output-title">${esc(p.filename)}</span>
    <a href="${esc(p.url)}" target="_blank" style="font-size:11px;color:var(--blue);">Preview →</a></div>
  `).join('') : '<div class="empty">No HTML previews generated yet</div>');
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
