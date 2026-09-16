(() => {
  const $ = (id) => document.getElementById(id);
  const state = { page: 1, pageSize: 20, query: '', status: 'all', pages: 1 };
  const settingsState = { providers: [], selected: [], saved: [], loaded: false };
  const api = () => {
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize, status: state.status });
    if (state.query) params.set('q', state.query);
    return fetch(`/api/admin-monitor/?${params}`, { cache: 'no-store' }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`${body.detail || 'Unable to load monitoring feed.'} (HTTP ${response.status})`);
      return body;
    });
  };
  const money = (value) => value == null ? '—' : Number(value).toFixed(2);
  const evOdds = (value) => value == null ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(6)}`;
  const evAmount = (value) => value == null ? '—' : `$${Number(value).toFixed(2)}`;
  const date = (value) => value ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Unknown time';
  const bookName = (book) => ({ draftkings: 'DraftKings', fanduel: 'FanDuel', pinnacle: 'Pinnacle', betmgm: 'BetMGM', caesars: 'Caesars' }[String(book).toLowerCase()] || book);
  const settingsApi = (path, options = {}) => fetch(path, { cache: 'no-store', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options }).then(async (response) => { const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || body.error || `Request failed (HTTP ${response.status})`); return body; });
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  function updateSettingsSummary() {
    const labels = settingsState.selected.map((id) => {
      const provider = settingsState.providers.find((item) => String(item.id || item.key).toLowerCase() === id);
      return provider?.name || bookName(id);
    });
    const dirty = settingsState.selected.slice().sort().join(',') !== settingsState.saved.slice().sort().join(',');
    $('savedBooksSummary').textContent = labels.length ? `${dirty ? 'Unsaved selection' : 'Configured'} · ${labels.join(', ')}` : 'No peer books selected';
    $('providerTrigger').querySelector('span').textContent = labels.length ? `${labels.length} selected · ${labels.join(', ')}` : 'Select comparison books';
  }
  function renderProviderSettings() {
    const list = $('providerOptions');
    const peers = settingsState.providers.filter((provider) => String(provider.id || provider.key || '').toLowerCase() !== 'draftkings');
    if (!peers.length) { list.innerHTML = '<div class="settings-loading">No comparison books are available right now.</div>'; return; }
    list.innerHTML = peers.map((provider) => { const id = String(provider.id || provider.key).toLowerCase(); const label = provider.name || bookName(id); const checked = settingsState.selected.includes(id) ? ' checked' : ''; return `<label class="provider-option"><input type="checkbox" value="${escapeHtml(id)}"${checked}><span class="provider-mark">${escapeHtml(label.slice(0, 2).toUpperCase())}</span><span><b>${escapeHtml(label)}</b><small>OpticOdds provider</small></span><i></i></label>`; }).join('');
    list.querySelectorAll('input').forEach((input) => input.addEventListener('change', () => { settingsState.selected = [...list.querySelectorAll('input:checked')].map((item) => item.value); updateSettingsButton(); }));
    settingsState.loaded = true;
    updateSettingsSummary();
    updateSettingsButton();
  }
  function updateSettingsButton() { const button = $('saveSettings'); if (!button) return; button.disabled = !settingsState.loaded || settingsState.selected.length < 1 || settingsState.selected.length > 4; updateSettingsSummary(); if (!settingsState.loaded) $('settingsStatus').textContent = 'Loading comparison settings…'; else $('settingsStatus').textContent = settingsState.selected.length ? `${settingsState.selected.length} comparison ${settingsState.selected.length === 1 ? 'book' : 'books'} selected` : 'Select at least one comparison book'; }
  async function loadProviderSettings() {
    try {
      const [catalog, preference] = await Promise.all([settingsApi('/api/odds/providers/'), settingsApi('/api/admin-sportsbook/settings/')]);
      settingsState.providers = catalog.providers || [];
      settingsState.selected = Array.isArray(preference.selected_books) ? preference.selected_books : ['fanduel', 'pinnacle'];
      settingsState.saved = [...settingsState.selected];
      renderProviderSettings();
    } catch (error) { $('providerOptions').innerHTML = `<div class="settings-loading error-text">${escapeHtml(error.message)}</div>`; $('settingsStatus').textContent = 'Unable to load comparison books'; }
  }
  async function saveProviderSettings() {
    const button = $('saveSettings'); button.disabled = true; $('settingsStatus').textContent = 'Saving comparison books…';
    try { await settingsApi('/api/admin-sportsbook/settings/', { method: 'POST', body: JSON.stringify({ selected_books: settingsState.selected }) }); settingsState.saved = [...settingsState.selected]; $('settingsStatus').textContent = 'Saved. New sportsbook prices will use these books.'; updateSettingsButton(); } catch (error) { $('settingsStatus').textContent = error.message; updateSettingsButton(); }
  }
  const cleanNote = (bet) => {
    if (bet.note) return bet.note;
    const providerLines = Object.entries(bet.provider_odds || {}).map(([book, line]) => `${bookName(book)}: ${money(line.decimal)}`).join(', ');
    const probability = bet.weighted_implied_probability == null ? '' : ` | Weighted implied probability: ${(Number(bet.weighted_implied_probability) * 100).toFixed(2)}%`;
    const audit = bet.is_potentially_bad ? ` | Audit: POTENTIALLY BAD — ${bet.audit_reason}` : ' | Audit: within selected market range';
    return `${bet.event || bet.selection} | ${money(bet.primary_decimal)} vs. ${providerLines}${probability}${audit}`;
  };
  function render(body) {
    const bets = body.bets || [];
    const pagination = body.pagination || {};
    state.pages = pagination.pages || 1;
    $('total').textContent = pagination.total ?? bets.length;
    $('flagged').textContent = pagination.flagged_total ?? bets.filter((bet) => bet.is_potentially_bad).length;
    $('alertCount').textContent = bets.some((bet) => bet.is_potentially_bad) ? '!' : '';
    $('updated').textContent = `Updated ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
    $('pageLabel').textContent = `Page ${pagination.page || state.page} of ${state.pages}`;
    $('previous').disabled = !pagination.has_previous;
    $('next').disabled = !pagination.has_next;
    if (!bets.length) { $('monitorList').innerHTML = '<div class="empty panel"><div>✓</div><h3>No matching records</h3><p>Try another search or status filter.</p></div>'; return; }
    $('monitorList').innerHTML = bets.map((bet) => {
      const odds = Object.entries(bet.provider_odds || {}).map(([book, line]) => `<span><b>${bookName(book)}</b> ${money(line.decimal)}</span>`).join('');
      const parlay = Number(bet.slip_leg_count || 1) > 1 ? `<span>parlay ${bet.slip_leg_count} legs · odds <b>${money(bet.slip_combined_decimal_odds)}</b></span><span>parlay EV_ODDS <b>${evOdds(bet.slip_ev_odds)}</b></span><span>parlay EV_AMT <b>${evAmount(bet.slip_ev_amount)}</b></span>` : '';
      return `<article class="monitor-card panel ${bet.is_potentially_bad ? 'flagged' : ''}"><div class="monitor-card-head"><div><div class="meta">${date(bet.created_at)} · ${bet.sport || 'sport'}${bet.league ? ` · ${bet.league}` : ''}</div><h3>${bet.event || bet.selection}</h3><div class="meta">${bet.market} · ${bet.selection}</div></div><span class="${bet.is_potentially_bad ? 'flag' : 'clear'}">${bet.is_potentially_bad ? 'REVIEW' : 'WITHIN RANGE'}</span></div><div class="monitor-note">${escapeHtml(cleanNote(bet))}</div><div class="monitor-foot">${odds}<span>DK baseline <b>${money(bet.primary_decimal)}</b></span>${bet.aggregate_comp_odds != null ? `<span>aggregate comp <b>${Number(bet.aggregate_comp_odds).toFixed(6)}</b></span>` : ''}<span>EV_ODDS <b>${evOdds(bet.ev_odds)}</b></span><span>EV_AMT <b>${evAmount(bet.ev_amount)}</b></span>${parlay}${bet.edge_decimal != null ? `<span>edge <b>${money(bet.edge_decimal)}</b></span>` : ''}</div></article>`;
    }).join('');
  }
  async function refresh() { $('refresh').disabled = true; try { render(await api()); } catch (error) { $('monitorList').innerHTML = `<div class="empty panel"><div>!</div><h3>Monitoring unavailable</h3><p>${error.message}</p></div>`; } finally { $('refresh').disabled = false; } }
  let searchTimer;
  $('search').addEventListener('input', (event) => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { state.query = event.target.value.trim(); state.page = 1; refresh(); }, 250); });
  $('statusFilter').addEventListener('change', (event) => { state.status = event.target.value; state.page = 1; refresh(); });
  $('pageSize').addEventListener('change', (event) => { state.pageSize = Number(event.target.value); state.page = 1; refresh(); });
  $('previous').addEventListener('click', () => { if (state.page > 1) { state.page -= 1; refresh(); } });
  $('next').addEventListener('click', () => { if (state.page < state.pages) { state.page += 1; refresh(); } });
  $('refresh').addEventListener('click', refresh);
  $('saveSettings').addEventListener('click', saveProviderSettings);
  $('settingsToggle').addEventListener('click', () => {
    const expanded = $('settingsToggle').getAttribute('aria-expanded') === 'true';
    $('settingsToggle').setAttribute('aria-expanded', String(!expanded));
    $('settingsBody').classList.toggle('hidden', expanded);
  });
  $('providerTrigger').addEventListener('click', (event) => { event.stopPropagation(); $('providerList').classList.toggle('open'); });
  document.addEventListener('click', (event) => { if (!$('providerList').contains(event.target)) $('providerList').classList.remove('open'); });
  if (window.location.hash === '#comparison-settings') $('settingsToggle').click();
  loadProviderSettings();
  refresh();
  setInterval(refresh, 15000);
})();
