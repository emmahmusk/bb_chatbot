(() => {
  const $ = (id) => document.getElementById(id);
  const state = { sports: [], leagues: [], fixtures: [], rows: [], overrides: [], activeSelection: '', books: ['draftkings', 'fanduel', 'pinnacle', 'bet365'] };
  const names = { draftkings: 'DraftKings', fanduel: 'FanDuel', pinnacle: 'Pinnacle', bet365: 'bet365', caesars: 'Caesars', betmgm: 'BetMGM' };
  // The Demo Odds Lab is deliberately local. It must remain usable when the
  // OpticOdds key or the EC2 admin-service key is expired/unavailable.
  const api = (path, options = {}) => fetch(`/api/demo-odds-lab/${path}`, { cache: 'no-store', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options }).then(async (response) => { const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || body.error || `Request failed (HTTP ${response.status})`); return body; });
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const bookName = (book) => names[String(book).toLowerCase()] || String(book).replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const american = (value) => { const number = Number(value); return Number.isFinite(number) ? `${number > 0 ? '+' : ''}${number}` : '—'; };
  const setError = (message = '') => { $('demoError').textContent = message; };
  const setOptions = (select, items, placeholder) => { select.innerHTML = `<option value="">${placeholder}</option>` + items.map((item) => `<option value="${escapeHtml(item.id || item.fixture_id)}">${escapeHtml(item.label || item.name || item.event || item.id || item.fixture_id)}</option>`).join(''); };
  const key = (row) => `${String(row.sportsbook).toLowerCase()}|${String(row.selection).toLowerCase()}`;
  const overrideKey = (book, selection) => `${String(book).toLowerCase()}|${String(selection).toLowerCase()}`;

  async function loadSports() {
    const body = await api('sports/'); state.sports = body.sports || []; setOptions($('demoSport'), state.sports, 'Choose a sport');
    if (state.sports[0]) { $('demoSport').value = state.sports[0].id; await loadLeagues(); }
  }
  async function loadLeagues() {
    const sport = $('demoSport').value; state.fixtures = []; state.activeSelection = ''; $('demoFixture').innerHTML = '<option value="">Choose a league first</option>'; $('demoSelectionTabs').innerHTML = ''; $('demoRows').innerHTML = '<div class="empty"><div>↗</div><h3>Choose a league</h3><p>Demo fixtures will appear here.</p></div>'; if (!sport) return;
    const body = await api(`leagues/?sport=${encodeURIComponent(sport)}`); state.leagues = body.leagues || []; setOptions($('demoLeague'), state.leagues, 'Choose a league');
  }
  async function loadFixtures() {
    const sport = $('demoSport').value; const league = $('demoLeague').value; if (!sport || !league) return;
    $('demoFixture').innerHTML = '<option value="">Loading fixtures…</option>';
    const body = await api(`fixtures/?sport=${encodeURIComponent(sport)}&league=${encodeURIComponent(league)}`); state.fixtures = body.fixtures || []; setOptions($('demoFixture'), state.fixtures, 'Choose a fixture');
    if (state.fixtures[0]) { $('demoFixture').value = state.fixtures[0].fixture_id; await showOdds(); }
  }
  async function showOdds() {
    const fixture = $('demoFixture').value; if (!fixture) return;
    setError(''); $('demoStatus').textContent = 'Loading demo prices…'; const market = $('demoMarket').value;
    const [body, overrideBody] = await Promise.all([api(`fixtures/${encodeURIComponent(fixture)}/odds/?sportsbooks=${state.books.join(',')}&market=${encodeURIComponent(market)}`), api(`demo-odds/?fixture_id=${encodeURIComponent(fixture)}`)]);
    state.rows = body.odds || []; state.overrides = overrideBody.overrides || []; $('demoTitle').textContent = state.fixtures.find((item) => item.fixture_id === fixture)?.event || fixture; $('demoStatus').textContent = `${state.rows.length} generated provider prices · edit a decimal price and save to model a movement.`; renderRows();
  }
  function renderRows() {
    const byKey = new Map(state.rows.map((row) => [key(row), row]));
    const overrideMap = new Map(state.overrides.map((item) => [overrideKey(item.sportsbook, item.selection), item]));
    const selections = [...new Set(state.rows.map((row) => row.selection))];
    if (!selections.includes(state.activeSelection)) state.activeSelection = selections[0] || '';

    // Keep the normal home / draw / away order returned by the demo service,
    // while presenting each outcome as a focused editing tab.
    $('demoSelectionTabs').innerHTML = selections.map((selection, index) => `<button class="demo-selection-tab ${selection === state.activeSelection ? 'active' : ''}" type="button" role="tab" aria-selected="${selection === state.activeSelection}" data-selection="${escapeHtml(selection)}"><span>${String(index + 1).padStart(2, '0')}</span><b>${escapeHtml(selection)}</b><small>${state.books.filter((book) => byKey.has(overrideKey(book, selection))).length} providers</small></button>`).join('');
    $('demoSelectionTabs').querySelectorAll('.demo-selection-tab').forEach((button) => button.addEventListener('click', () => { state.activeSelection = button.dataset.selection; renderRows(); }));

    const selection = state.activeSelection;
    const html = state.books.map((book) => {
      const row = byKey.get(overrideKey(book, selection));
      if (!row) return '';
      const override = overrideMap.get(overrideKey(book, selection));
      const value = override ? override.decimal_odds : row.decimal;
      return `<div class="demo-row ${override ? 'overridden' : ''}" data-book="${escapeHtml(book)}" data-selection="${escapeHtml(selection)}"><div class="demo-row-head"><b>${escapeHtml(bookName(book))}${override ? '<span class="demo-badge">OVERRIDE</span>' : ''}</b><span class="demo-row-label">${escapeHtml(selection)} · ${escapeHtml(row.market || 'Moneyline')}</span></div><label><span class="demo-row-label">Decimal odds</span><input class="demo-odds-input" type="number" min="1.01" step="0.01" value="${Number(value).toFixed(2)}" aria-label="${escapeHtml(bookName(book))} ${escapeHtml(selection)} decimal odds"><small>American ${american(override ? override.american_price : row.price)}</small></label><div><span class="demo-row-label">Provider</span><small>${override ? 'Saved demo movement' : 'Generated demo price'}</small></div><div class="demo-row-actions"><button class="save-override" type="button">Save</button>${override ? '<button class="clear-override" type="button">Clear</button>' : ''}</div></div>`;
    }).join('');
    $('demoRows').innerHTML = html || '<div class="empty"><div>—</div><h3>No demo prices found</h3><p>Try another fixture or market.</p></div>';
    $('demoRows').querySelectorAll('.save-override').forEach((button) => button.addEventListener('click', () => saveOverride(button.closest('.demo-row'))));
    $('demoRows').querySelectorAll('.clear-override').forEach((button) => button.addEventListener('click', () => clearOverride(button.closest('.demo-row'))));
  }
  async function saveOverride(row) {
    const decimal = Number(row.querySelector('.demo-odds-input').value); if (!Number.isFinite(decimal) || decimal <= 1) { setError('Decimal odds must be greater than 1.00.'); return; }
    row.querySelectorAll('button').forEach((button) => { button.disabled = true; });
    try { await api('demo-odds/', { method: 'POST', body: JSON.stringify({ fixture_id: $('demoFixture').value, sportsbook: row.dataset.book, market: $('demoMarket').value, selection: row.dataset.selection, decimal_odds: decimal }) }); await showOdds(); } catch (error) { setError(error.message); } finally { row.querySelectorAll('button').forEach((button) => { button.disabled = false; }); }
  }
  async function clearOverride(row) {
    try { await api('demo-odds/', { method: 'DELETE', body: JSON.stringify({ fixture_id: $('demoFixture').value, sportsbook: row.dataset.book, market: $('demoMarket').value, selection: row.dataset.selection }) }); await showOdds(); } catch (error) { setError(error.message); }
  }
  $('demoSport').addEventListener('change', loadLeagues); $('demoLeague').addEventListener('change', loadFixtures); $('demoFixture').addEventListener('change', showOdds); $('demoMarket').addEventListener('change', showOdds);
  loadSports().catch((error) => setError(error.message));
})();
