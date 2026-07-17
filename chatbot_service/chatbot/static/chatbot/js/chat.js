(() => {
  const form = document.querySelector('#chatForm');
  const input = document.querySelector('#messageInput');
  const messages = document.querySelector('#messages');
  const sendButton = document.querySelector('#sendButton');
  const clearButton = document.querySelector('#clearButton');
  const errorBanner = document.querySelector('#errorBanner');
  const marketCount = document.querySelector('#marketCount');
  const dataStatus = document.querySelector('#dataStatus');
  const initialWelcome = document.querySelector('.welcome-message').outerHTML;
  let history = [];
  let busy = false;

  const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
  const scrollDown = () => { messages.scrollTop = messages.scrollHeight; };

  function formatStructuredAnswer(answer) {
    if (!answer || typeof answer.summary !== 'string' || !Array.isArray(answer.sections)) return '';
    const sections = answer.sections.map(section => {
      const points = Array.isArray(section.points) ? section.points : [];
      const pointHtml = points.map(point => {
        const style = ['standard', 'insight', 'calculation', 'caution'].includes(point.style) ? point.style : 'standard';
        return `<div class="answer-point ${style}"><strong>${escapeHtml(point.label || '')}:</strong><span>${escapeHtml(point.text || '')}</span></div>`;
      }).join('');
      return `<section class="answer-section"><h3>${escapeHtml(section.heading || '')}</h3><div class="answer-points">${pointHtml}</div></section>`;
    }).join('');
    return `<p class="answer-summary">${escapeHtml(answer.summary)}</p>${sections}<p class="answer-disclaimer">${escapeHtml(answer.disclaimer || '')}</p>`;
  }

  function addUserMessage(text) {
    messages.insertAdjacentHTML('beforeend', `<article class="message user-message"><div class="message-body"><div class="bubble"><p>${escapeHtml(text)}</p></div></div></article>`);
    scrollDown();
  }

  function addAssistantMessage(answer, structuredAnswer, sources = []) {
    const unique = [...new Map(sources.map(source => [source.market_id, source])).values()].slice(0, 6);
    const chips = unique.length ? `<div class="sources">${unique.map(source => `<span class="source-chip"><strong>${escapeHtml(source.symbol)}</strong> &middot; ${escapeHtml(source.expiry_date || 'no expiry')} &middot; ${escapeHtml(source.implied_probability_over || 'N/A')} over</span>`).join('')}</div>` : '';
    const content = formatStructuredAnswer(structuredAnswer) || `<p>${escapeHtml(answer)}</p>`;
    messages.insertAdjacentHTML('beforeend', `<article class="message assistant-message"><div class="avatar"><span>BB</span></div><div class="message-body"><div class="message-meta">BULLBEAR ANALYSIS</div><div class="bubble">${content}</div>${chips}</div></article>`);
    scrollDown();
  }

  function showTyping() {
    messages.insertAdjacentHTML('beforeend', '<article class="message assistant-message" id="typingMessage"><div class="avatar"><span>BB</span></div><div class="message-body"><div class="bubble"><div class="typing"><i></i><i></i><i></i></div></div></div></article>');
    scrollDown();
  }

  async function send(text) {
    if (busy || !text.trim()) return;
    busy = true;
    sendButton.disabled = true;
    errorBanner.classList.remove('show');
    document.querySelector('#suggestions')?.remove();
    addUserMessage(text);
    showTyping();
    input.value = '';
    resizeInput();
    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: text, history: history.slice(-8)})
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || body.detail || `Request failed (${response.status})`);
      document.querySelector('#typingMessage')?.remove();
      addAssistantMessage(body.answer, body.structured_answer, body.sources);
      history.push({role: 'user', content: text}, {role: 'assistant', content: body.answer});
    } catch (error) {
      document.querySelector('#typingMessage')?.remove();
      errorBanner.textContent = error.message;
      errorBanner.classList.add('show');
    } finally {
      busy = false;
      sendButton.disabled = false;
      input.focus();
    }
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  }

  form.addEventListener('submit', event => { event.preventDefault(); send(input.value); });
  input.addEventListener('input', resizeInput);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
  });
  messages.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (button?.closest('#suggestions')) send(button.querySelector('span:nth-child(2)').textContent);
  });
  clearButton.addEventListener('click', () => {
    if (busy) return;
    history = [];
    messages.innerHTML = initialWelcome;
    errorBanner.classList.remove('show');
    messages.scrollTop = 0;
    input.focus();
  });

  fetch('/api/health/').then(response => response.json()).then(body => {
    marketCount.textContent = `${Number(body.indexed_markets || 0).toLocaleString()} markets indexed`;
    dataStatus.textContent = body.indexed_markets ? 'Ready for grounded questions' : 'Index will sync on your first question';
  }).catch(() => {
    marketCount.textContent = 'Market service unavailable';
    dataStatus.textContent = 'Check the service configuration';
  });
})();
