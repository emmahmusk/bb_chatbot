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
  const conversationStorageKey = 'bullbear_active_conversation';
  let conversationId = readConversationId();
  let busy = false;

  const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
  const scrollDown = () => { messages.scrollTop = messages.scrollHeight; };

  function readConversationId() {
    try { return window.localStorage.getItem(conversationStorageKey); }
    catch (_) { return null; }
  }

  function rememberConversation(id) {
    conversationId = id || null;
    try {
      if (conversationId) window.localStorage.setItem(conversationStorageKey, conversationId);
      else window.localStorage.removeItem(conversationStorageKey);
    } catch (_) { /* Conversation still works for the current page. */ }
  }

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
        body: JSON.stringify({
          message: text,
          ...(conversationId ? {conversation_id: conversationId} : {})
        })
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || body.detail || `Request failed (${response.status})`);
      rememberConversation(body.conversation_id);
      document.querySelector('#typingMessage')?.remove();
      addAssistantMessage(body.answer, body.structured_answer, body.sources || []);
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
    rememberConversation(null);
    messages.innerHTML = initialWelcome;
    errorBanner.classList.remove('show');
    messages.scrollTop = 0;
    input.focus();
  });

  async function restoreConversation() {
    if (!conversationId) return;
    busy = true;
    sendButton.disabled = true;
    try {
      const response = await fetch(`/api/conversations/${encodeURIComponent(conversationId)}/`);
      if (response.status === 404) {
        rememberConversation(null);
        return;
      }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || 'Could not restore the conversation.');
      if (!Array.isArray(body.messages) || !body.messages.length) return;

      messages.innerHTML = '';
      for (const message of body.messages) {
        if (message.role === 'user') addUserMessage(message.content);
        if (message.role === 'assistant') {
          addAssistantMessage(message.content, message.structured_answer, message.sources || []);
        }
      }
      scrollDown();
    } catch (error) {
      errorBanner.textContent = error.message;
      errorBanner.classList.add('show');
    } finally {
      busy = false;
      sendButton.disabled = false;
    }
  }

  fetch('/api/health/').then(response => response.json()).then(body => {
    marketCount.textContent = `${Number(body.indexed_markets || 0).toLocaleString()} markets indexed`;
    dataStatus.textContent = !body.indexed_markets
      ? 'Index will sync on your first question'
      : body.index_complete
        ? 'Complete expiry coverage ready'
        : 'Refresh required for complete expiries';
  }).catch(() => {
    marketCount.textContent = 'Market service unavailable';
    dataStatus.textContent = 'Check the service configuration';
  });

  restoreConversation();
})();
