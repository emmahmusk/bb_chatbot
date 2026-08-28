(() => {
  const $ = (id) => document.getElementById(id);
  const trigger = $('providerTrigger');
  const options = $('providerOptions');
  const note = $('selectionNote');
  const error = $('formError');
  const compare = $('compareButton');
  const preview = $('previewBanner');
  let providers = [];

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
      const response = await fetch('/api/odds/providers/');
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'Could not load providers.');
      providers = body.providers || [];
      renderProviders();
      if (body.preview) preview.classList.remove('hidden'); else preview.classList.add('hidden');
    } catch (e) { error.textContent = e.message; providers = []; }
  };
  trigger.addEventListener('click', () => $('providerSelect').classList.toggle('open'));
  document.addEventListener('click', (event) => { if (!$('providerSelect').contains(event.target)) $('providerSelect').classList.remove('open'); });

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
  loadProviders();
})();
