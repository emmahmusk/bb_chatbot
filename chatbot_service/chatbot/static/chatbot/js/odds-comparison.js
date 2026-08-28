(() => {
  const $ = (id) => document.getElementById(id);
  const trigger = $('providerTrigger');
  const options = $('providerOptions');
  const note = $('selectionNote');
  const error = $('formError');
  const compare = $('compareButton');
  const preview = $('previewBanner');
  const sportSelect = $('sport');
  const leagueSelect = $('league');
  const marketSelect = $('market');
  const fixtureSelect = $('fixtureId');
  let providers = [];
  let catalogController = null;
  const FALLBACK_PROVIDERS = ['DraftKings', 'BetMGM', 'FanDuel', 'Caesars', 'bet365', 'Fanatics Sportsbook'].map((name) => ({id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name}));
  const FALLBACK_SPORTS = [{id:'basketball',name:'Basketball'},{id:'football',name:'Football'},{id:'soccer',name:'Soccer'}];
  const FALLBACK_LEAGUES = [{id:'nba',name:'NBA'},{id:'ncaab',name:'NCAAB'},{id:'wnba',name:'WNBA'}];
  const FALLBACK_MARKETS = [{id:'moneyline',name:'Moneyline'},{id:'point_spread',name:'Point Spread'},{id:'total_points',name:'Total Points'}];
  const fetchWithTimeout = (url, options = {}, timeout = 8000) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    if (options.signal) options.signal.addEventListener('abort', () => controller.abort(), {once: true});
    return fetch(url, {...options, signal: controller.signal}).finally(() => clearTimeout(timer));
  };

  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const selected = () => [...options.querySelectorAll('input:checked')].map((input) => input.value);
  const selectedLabels = () => [...options.querySelectorAll('input:checked')].map((input) => input.dataset.label || input.value);
  const syncSelection = () => {
    const values = selectedLabels();
    const summary = values.length > 2 ? `${values.slice(0, 2).join(', ')} +${values.length - 2}` : values.join(', ');
    trigger.querySelector('span').textContent = values.length ? summary : 'Select sportsbooks';
    options.querySelectorAll('input:not(:checked)').forEach((input) => { input.disabled = values.length >= 5; });
    note.textContent = values.length < 2 ? 'Select at least two providers.' : `${values.length} providers selected · maximum 5`;
    note.style.color = values.length < 2 ? '#748195' : '#62dca6';
  };
  const renderProviders = () => {
    options.innerHTML = providers.map((book) => `<label class="option"><input type="checkbox" value="${esc(book.id || book.name)}" data-label="${esc(book.name || book.id)}"><span>${esc(book.name || book.id)}</span></label>`).join('');
    options.querySelectorAll('input').forEach((input) => input.addEventListener('change', syncSelection));
    syncSelection();
  };
  const loadProviders = async () => {
    try {
      const response = await fetchWithTimeout('/api/odds/providers/');
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not load providers.');
      providers = body.providers || [];
      renderProviders();
      if (body.preview) preview.classList.remove('hidden'); else preview.classList.add('hidden');
    } catch (e) { providers = FALLBACK_PROVIDERS; renderProviders(); preview.classList.remove('hidden'); if (e.name !== 'AbortError') error.textContent = 'Live providers are taking longer than expected. Preview providers are ready.'; }
  };
  const setOptions = (select, items, placeholder) => {
    select.innerHTML = `<option value="">${esc(placeholder)}</option>` + (items || []).map((item) => `<option value="${esc(item.id || item.name)}">${esc(item.name || item.id)}</option>`).join('');
    select.disabled = !(items || []).length;
  };
  const setFixtureOptions = (items) => {
    fixtureSelect.innerHTML = `<option value="">${esc(items?.length ? 'Select a fixture' : 'No upcoming fixtures')}</option>` + (items || []).map((fixture) => {
      const date = fixture.is_live ? 'Live now' : (fixture.start_date ? new Date(fixture.start_date).toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}) : 'Preview');
      return `<option value="${esc(fixture.id)}">${esc(fixture.label)} · ${esc(date)}</option>`;
    }).join('');
    fixtureSelect.disabled = !(items || []).length;
    if (items?.length === 1) fixtureSelect.value = items[0].id;
  };
  const loadCatalog = async (sport = sportSelect.value, league = '', bootstrap = false) => {
    try {
      catalogController?.abort();
      catalogController = new AbortController();
      const response = await fetchWithTimeout(`/api/odds/catalog/?sport=${encodeURIComponent(sport)}${league ? `&league=${encodeURIComponent(league)}` : ''}${bootstrap ? '&bootstrap=1' : ''}`, {signal: catalogController.signal});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not load market options.');
      const currentLeague = league;
      setOptions(sportSelect, body.sports, 'Select sport');
      if (sportSelect.value !== sport) sportSelect.value = sport;
      if (bootstrap) {
        if (body.preview) preview.classList.remove('hidden'); else preview.classList.add('hidden');
        return;
      }
      setOptions(leagueSelect, body.leagues, body.leagues?.length ? 'Select league' : 'No active leagues');
      if (currentLeague && [...leagueSelect.options].some((option) => option.value === currentLeague)) leagueSelect.value = currentLeague;
      setOptions(marketSelect, body.markets, body.markets?.length ? 'Select market' : 'No markets available');
      if (body.markets?.length) marketSelect.value = body.markets[0].id;
      setFixtureOptions(body.fixtures);
      if (body.preview) preview.classList.remove('hidden'); else preview.classList.add('hidden');
    } catch (e) {
      if (e.name === 'AbortError') return;
      if (bootstrap) setOptions(sportSelect, FALLBACK_SPORTS, 'Select sport');
      setOptions(leagueSelect, FALLBACK_LEAGUES, 'Select league');
      setOptions(marketSelect, FALLBACK_MARKETS, 'Select market');
      setFixtureOptions([{id:'preview-basketball-001', label:'Celtics @ Lakers', start_date:null}]);
      preview.classList.remove('hidden');
      error.textContent = 'Live market options are taking longer than expected. Preview options are ready.';
    }
  };
  trigger.addEventListener('click', () => $('providerSelect').classList.toggle('open'));
  document.addEventListener('click', (event) => { if (!$('providerSelect').contains(event.target)) $('providerSelect').classList.remove('open'); });
  sportSelect.addEventListener('change', () => loadCatalog(sportSelect.value));
  leagueSelect.addEventListener('change', () => loadCatalog(sportSelect.value, leagueSelect.value));

  const formatPrice = (price) => { if (price === null || price === undefined || price === '') return '—'; const number = Number(price); return Number.isFinite(number) ? (number > 0 ? `+${number}` : `${number}`) : String(price); };
  const formatTime = (value) => { if (!value) return 'Just now'; const numeric = Number(value); const date = Number.isFinite(numeric) ? new Date(numeric > 100000000000 ? numeric : numeric * 1000) : new Date(value); return Number.isNaN(date.getTime()) ? 'Live' : date.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'}); };
  const renderResults = (body) => {
    $('emptyResults').classList.add('hidden'); $('tableWrap').classList.remove('hidden'); $('resultFoot').classList.remove('hidden'); $('mobileResults').classList.remove('hidden');
    $('resultCount').textContent = `${body.count} price${body.count === 1 ? '' : 's'} compared`;
    const rows = body.rows || [];
    $('resultsBody').innerHTML = rows.map((row) => `<tr><td>${esc(row.sportsbook)}</td><td class="event">${esc(row.event)}<div class="market-label">${esc(row.market)}</div></td><td>${esc(row.selection)}${row.points !== null && row.points !== undefined ? ` <small>${esc(row.points)}</small>` : ''}</td><td class="price">${formatPrice(row.price)}</td><td class="decimal">${row.decimal ?? '—'}</td><td>${formatTime(row.updated_at)}</td></tr>`).join('');
    $('mobileResults').innerHTML = rows.map((row) => `<article class="mobile-row"><div class="mobile-row-top"><span class="mobile-book">${esc(row.sportsbook)}</span><span class="mobile-price">${formatPrice(row.price)} <small>${row.decimal ?? ''}</small></span></div><div class="mobile-event">${esc(row.selection)}</div><div class="mobile-meta">${esc(row.event)} · ${esc(row.market)}</div></article>`).join('');
    $('updated').textContent = `Updated ${new Date().toLocaleTimeString([], {hour:'numeric', minute:'2-digit'})}`;
  };
  compare.addEventListener('click', async () => {
    error.textContent = ''; const books = selected();
    if (books.length < 2 || books.length > 5) { error.textContent = 'Choose between 2 and 5 providers.'; return; }
    compare.disabled = true; compare.querySelector('span').textContent = 'Comparing…';
    try {
      const response = await fetch('/api/odds/compare/', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sport:$('sport').value, fixture_id:$('fixtureId').value.trim(), league:$('league').value.trim(), market:$('market').value, sportsbooks:books})});
      const body = await response.json(); if (!response.ok) throw new Error(body.error || `Request failed (${response.status}).`);
      renderResults(body); if (body.preview) preview.classList.remove('hidden'); else preview.classList.add('hidden');
    } catch (e) { error.textContent = e.message; } finally { compare.disabled = false; compare.querySelector('span').textContent = 'Compare odds'; }
  });
  providers = FALLBACK_PROVIDERS;
  renderProviders();
  setOptions(sportSelect, FALLBACK_SPORTS, 'Select sport');
  sportSelect.value = 'basketball';
  setOptions(leagueSelect, FALLBACK_LEAGUES, 'Select league');
  setOptions(marketSelect, FALLBACK_MARKETS, 'Select market');
  marketSelect.value = 'moneyline';
  setFixtureOptions([{id:'preview-basketball-001', label:'Celtics @ Lakers', start_date:null}]);
  loadProviders();
  loadCatalog('basketball', '', true);
})();
