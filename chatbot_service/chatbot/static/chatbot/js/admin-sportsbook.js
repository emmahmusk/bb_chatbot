(() => {
  const $ = (id) => document.getElementById(id);
  const state = { sports: [], leagues: [], fixtures: [], rows: [], books: ['hardrockbet', 'fanduel', 'pinnacle', 'bet365'], selectedFixture: null };
  const names = { hardrockbet: 'Hard Rock', hardrock: 'Hard Rock', draftkings: 'DraftKings', fanduel: 'FanDuel', pinnacle: 'Pinnacle', betmgm: 'BetMGM', caesars: 'Caesars', bet365: 'bet365', fanatics: 'Fanatics' };
  const api = (path, options = {}) => fetch(`/api/admin-sportsbook/${path}`, { cache: 'no-store', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options }).then(async (response) => { const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(`${body.detail || body.error || 'The admin server returned an error.'} (HTTP ${response.status})`); return body; });
  const setError = (message = '') => { $('error').textContent = message; };
  const bookName = (id) => names[String(id).toLowerCase()] || String(id).replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const american = (value) => { if (value === null || value === undefined || value === '') return '—'; const number = Number(value); return Number.isFinite(number) ? `${number > 0 ? '+' : ''}${number}` : String(value); };
  const money = (value) => value == null ? '—' : Number(value).toFixed(2);

  const setOptions = (select, items, placeholder) => { select.innerHTML = `<option value="">${placeholder}</option>` + items.map((item) => `<option value="${item.id || item.fixture_id}">${item.label || item.name || item.event || item.id || item.fixture_id}</option>`).join(''); };

  async function loadSettings() {
    try {
      const body = await api('settings/');
      const peers = Array.isArray(body.selected_books) ? body.selected_books : ['fanduel', 'pinnacle'];
      state.books = ['hardrockbet', ...peers.filter((book) => !['hardrockbet', 'hardrock'].includes(book)).slice(0, 4)];
    } catch (error) {
      state.books = ['hardrockbet', 'fanduel', 'pinnacle', 'bet365'];
    }
  }

  async function loadSports() {
    const body = await api('sports/');
    state.sports = body.sports || [];
    setOptions($('sport'), state.sports, 'Choose a sport');
    const first = state.sports[0];
    if (first) { $('sport').value = first.id; await loadLeagues(); }
  }

  async function loadLeagues() {
    const sport = $('sport').value;
    state.fixtures = [];
    $('fixtureRail').classList.add('hidden');
    $('fixture').innerHTML = '<option value="">Choose a league first</option>';
    $('fixtureMeta').textContent = '';
    $('oddsGrid').innerHTML = '<div class="empty"><div>↗</div><h3>Choose a league</h3><p>The first five upcoming fixtures will appear here.</p></div>';
    $('boardTitle').textContent = 'Choose a league';
    $('boardStatus').textContent = 'Waiting for selection';
    if (!sport) return;
    const body = await api(`leagues/?sport=${encodeURIComponent(sport)}`);
    state.leagues = body.leagues || [];
    setOptions($('league'), state.leagues, 'Choose a league');
  }

  const fixtureLabel = (fixture) => `${fixture.is_live ? 'LIVE · ' : ''}${fixture.event || fixture.fixture_id}`;

  function renderFixtureRail() {
    const upcoming = state.fixtures.filter((fixture) => !fixture.is_live);
    const visible = (upcoming.length ? upcoming : state.fixtures).slice(0, 5);
    const rail = $('fixtureRail');
    if (!visible.length) { rail.classList.add('hidden'); return; }
    rail.classList.remove('hidden');
    rail.innerHTML = `<div class="fixture-rail-label">${upcoming.length ? 'UPCOMING FIXTURES' : 'LIVE FIXTURES'}<small>${upcoming.length ? `${upcoming.length} available` : 'in play now'}</small></div>${visible.map((fixture) => `<button class="fixture-chip ${fixture.fixture_id === state.selectedFixture?.fixture_id ? 'active' : ''}" data-fixture="${fixture.fixture_id}"><b>${fixture.event || fixture.fixture_id}</b><small>${fixture.start_date ? new Date(fixture.start_date).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : (fixture.is_live ? 'Live now' : 'Upcoming')}</small></button>`).join('')}`;
    rail.querySelectorAll('[data-fixture]').forEach((button) => button.addEventListener('click', () => selectFixture(button.dataset.fixture)));
  }

  async function loadFixtures() {
    const sport = $('sport').value;
    const league = $('league').value;
    if (!sport || !league) return;
    $('fixture').innerHTML = '<option value="">Loading upcoming fixtures…</option>';
    $('fixtureMeta').textContent = 'Loading…';
    const live = $('liveOnly').checked;
    const params = new URLSearchParams({ sport, league, ...(live ? { live_only: 'true' } : {}) });
    try {
      const body = await api(`fixtures/?${params}`);
      state.fixtures = (body.fixtures || []).sort((a, b) => { if (Boolean(a.is_live) !== Boolean(b.is_live)) return a.is_live ? -1 : 1; const aTime = a.start_date ? new Date(a.start_date).getTime() : Number.MAX_SAFE_INTEGER; const bTime = b.start_date ? new Date(b.start_date).getTime() : Number.MAX_SAFE_INTEGER; return aTime - bTime; });
      setOptions($('fixture'), state.fixtures.map((fixture) => ({ ...fixture, id: fixture.fixture_id, label: fixtureLabel(fixture) })), 'Choose a fixture');
      $('fixtureMeta').textContent = `${state.fixtures.length} available · first 5 shown`;
      const first = state.fixtures.filter((fixture) => !fixture.is_live)[0] || state.fixtures[0];
      if (first) { $('fixture').value = first.fixture_id; state.selectedFixture = first; renderFixtureRail(); await showOdds(first.fixture_id); }
      else { renderFixtureRail(); $('oddsGrid').innerHTML = '<div class="empty"><div>—</div><h3>No upcoming fixtures</h3><p>Try another league or turn off the live-only filter.</p></div>'; }
    } catch (error) {
      setError(error.message);
      $('fixture').innerHTML = '<option value="">Unable to load fixtures</option>';
      $('fixtureMeta').textContent = '';
    }
  }

  function selectFixture(fixtureId) {
    const fixture = state.fixtures.find((item) => item.fixture_id === fixtureId);
    if (!fixture) return;
    $('fixture').value = fixtureId;
    state.selectedFixture = fixture;
    renderFixtureRail();
    showOdds(fixtureId);
  }

  function renderRows(rows) {
    const groups = {};
    rows.forEach((row) => { const key = `${row.market}|${row.selection}|${row.points ?? ''}`; (groups[key] ||= []).push(row); });
    const providers = state.books;
    const cards = Object.values(groups).map((group) => {
      const baseline = group.find((row) => ['hardrockbet', 'hardrock'].includes(String(row.sportsbook).toLowerCase()));
      if (!baseline) return '';
      const byBook = Object.fromEntries(group.map((row) => [String(row.sportsbook).toLowerCase(), row]));
      const prices = providers.map((book) => {
        const row = byBook[book];
        if (!row) return `<div class="price-cell unavailable"><span>${bookName(book)}</span><b>—</b></div>`;
        const content = `<span>${bookName(book)}</span><b>${money(row.decimal)}</b><small>${american(row.price)}</small>`;
        return ['hardrockbet', 'hardrock'].includes(book) ? `<button class="price-cell selectable" data-selection="${encodeURIComponent(baseline.selection)}" data-market="${encodeURIComponent(baseline.market)}">${content}</button>` : `<div class="price-cell">${content}</div>`;
      }).join('');
      return `<article class="market-row"><div class="outcome"><small>${baseline.event || state.selectedFixture?.event || 'Selected fixture'}</small><strong>${baseline.selection || 'Selection'}</strong><span>${baseline.market}${baseline.points != null ? ` · ${baseline.points}` : ''}</span></div><div class="price-grid">${prices}</div></article>`;
    }).join('');
    $('oddsGrid').innerHTML = cards ? `<div class="market-board"><div class="market-board-head"><span>OUTCOME</span><div>${providers.map((book) => `<span>${bookName(book)}</span>`).join('')}</div></div>${cards}</div>` : '<div class="empty"><div>—</div><h3>No Hard Rock lines found</h3><p>Try another market or fixture.</p></div>';
    $('oddsGrid').querySelectorAll('.selectable').forEach((button) => button.addEventListener('click', () => recordBet(decodeURIComponent(button.dataset.selection), decodeURIComponent(button.dataset.market), button)));
  }

  async function showOdds(fixtureId = $('fixture').value) {
    setError('');
    if (!fixtureId) return;
    const market = $('market').value;
    const params = new URLSearchParams({ sportsbooks: state.books.join(','), market });
    $('boardStatus').textContent = 'Updating prices…';
    try {
      const body = await api(`fixtures/${encodeURIComponent(fixtureId)}/odds/?${params}`);
      state.rows = body.odds || [];
      state.selectedFixture = state.fixtures.find((fixture) => fixture.fixture_id === fixtureId) || state.selectedFixture;
      $('boardTitle').textContent = state.selectedFixture?.event || 'Selected fixture';
      $('boardStatus').textContent = state.selectedFixture?.is_live ? 'LIVE NOW' : 'UPCOMING';
      $('boardStatus').classList.toggle('live', !!state.selectedFixture?.is_live);
      renderFixtureRail();
      renderRows(state.rows);
    } catch (error) {
      setError(error.message);
      $('boardStatus').textContent = 'Unable to load prices';
    }
  }

  async function recordBet(selection, market, button) {
    button.disabled = true;
    button.classList.add('saving');
    button.querySelector('b').textContent = 'Saving…';
    try {
      const body = await api('bets/', { method: 'POST', body: JSON.stringify({ fixture_id: $('fixture').value, event: state.selectedFixture?.event || '', sport: $('sport').value, league: $('league').value, market, selection, sportsbook: 'hardrockbet', sportsbooks: state.books, odds_snapshot: state.rows }) });
      $('ticket').classList.remove('hidden');
      $('ticketNote').textContent = body.note || 'The selection and provider snapshot were recorded.';
      window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    } catch (error) {
      setError(error.message);
    } finally {
      button.disabled = false;
      button.classList.remove('saving');
      button.querySelector('b').textContent = money(state.rows.find((row) => ['hardrockbet', 'hardrock'].includes(String(row.sportsbook).toLowerCase()) && row.selection === selection)?.decimal);
    }
  }

  $('sport').addEventListener('change', loadLeagues);
  $('league').addEventListener('change', loadFixtures);
  $('fixture').addEventListener('change', (event) => selectFixture(event.target.value));
  $('liveOnly').addEventListener('change', loadFixtures);
  $('market').addEventListener('change', () => showOdds());
  Promise.resolve(loadSettings()).then(() => loadSports()).catch((error) => setError(error.message));
})();
