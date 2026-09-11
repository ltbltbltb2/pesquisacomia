(() => {
  'use strict';
  const input = document.querySelector('#search');
  const cards = [...document.querySelectorAll('[data-search]')];
  const buttons = [...document.querySelectorAll('[data-filter]')];
  const allowedThemes = ['Saúde', 'Clima', 'Finanças públicas', 'Energia', 'Preços'];
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const words = value => normalize(value).match(/[\p{L}\p{N}]+/gu) || [];
  const stopwords = new Set(['a', 'as', 'o', 'os', 'e', 'de', 'da', 'das', 'do', 'dos', 'no', 'nos', 'na', 'nas', 'em', 'com', 'para']);
  const number = word => /^\d+$/.test(word) ? String(Number(word)) : word;
  let theme = 'Todas';
  function stateFromURL() {
    const params = new URL(location.href).searchParams;
    return { query: (params.get('q') || '').slice(0, 200), theme: allowedThemes.includes(params.get('tema')) ? params.get('tema') : 'Todas' };
  }
  function searchParams(query, selectedTheme) {
    const params = new URLSearchParams();
    if (query.trim()) params.set('q', query.trim());
    if (selectedTheme !== 'Todas') params.set('tema', selectedTheme);
    return params.toString();
  }
  function updateLinks(query, selectedTheme) {
    const params = searchParams(query, selectedTheme);
    for (const link of document.querySelectorAll('[data-acervo], [data-study]')) {
      const url = new URL(link.getAttribute('href'), location.href);
      url.search = params;
      link.setAttribute('href', url.pathname + url.search + url.hash);
    }
  }
  function filter(saveURL = true) {
    const query = input.value.trim();
    const article = normalize(query).match(/\b(?:artigos?|pesquisas?)\s*0*(\d+)\b/);
    const bareId = /^0*[1-5]$/.test(query) ? query : null;
    const requestedId = article ? Number(article[1]) : bareId ? Number(bareId) : null;
    const remainingQuery = article ? normalize(query).replace(article[0], '') : query;
    const terms = words(remainingQuery).filter(word => !stopwords.has(word)).map(number);
    let count = 0;
    for (const card of cards) {
      const indexed = words(card.dataset.search).map(number);
      const matches = (requestedId === null || Number(card.dataset.id) === requestedId) && (theme === 'Todas' || card.dataset.themes.split('|').includes(theme)) &&
        terms.every(term => indexed.some(word => /^\d+$/.test(term) ? word === term : word.includes(term)));
      card.hidden = !matches;
      if (matches) count++;
    }
    for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.filter === theme));
    const context = [query ? `busca “${query}”` : '', theme !== 'Todas' ? `tema ${theme}` : ''].filter(Boolean).join(' · ');
    document.querySelector('.results-count').textContent = `${count} ${count === 1 ? 'pesquisa encontrada' : 'pesquisas encontradas'}${context ? ` · ${context}` : ''}.`;
    document.querySelector('.empty').hidden = count !== 0;
    document.querySelector('#empty-message').textContent = `Nenhuma pesquisa corresponde${context ? ` à ${context}` : ' à seleção'}. Experimente menos palavras ou limpe a busca e os filtros.`;
    for (const button of document.querySelectorAll('[data-clear-search]')) button.hidden = !query && theme === 'Todas';
    if (saveURL) {
      const url = new URL(location.href);
      url.search = searchParams(query, theme);
      if (url.href !== location.href) history.replaceState(null, '', url);
    }
    updateLinks(query, theme);
  }
  function restore() {
    const state = stateFromURL();
    if (input) { input.value = state.query; theme = state.theme; filter(false); }
    else updateLinks(state.query, state.theme);
  }
  if (input) {
    document.querySelector('.search-controls').hidden = false;
    document.querySelector('.results-count').hidden = false;
    input.addEventListener('input', () => filter());
    for (const button of buttons) button.addEventListener('click', () => { theme = button.dataset.filter; filter(); });
    for (const button of document.querySelectorAll('[data-clear-search]')) button.addEventListener('click', () => {
      input.value = ''; theme = 'Todas'; filter(); input.focus();
    });
  }
  restore();
  addEventListener('pageshow', restore);
  addEventListener('popstate', restore);
  const zoom = document.querySelector('#chart-zoom');
  if (zoom) {
    zoom.hidden = false;
    zoom.addEventListener('click', () => {
      const enlarged = document.querySelector('.chart-scroll').classList.toggle('enlarged');
      zoom.setAttribute('aria-pressed', String(enlarged));
      zoom.textContent = enlarged ? 'Ajustar à tela' : 'Ampliar gráfico';
    });
  }
})();

(() => {
  const input = document.querySelector('#verify-file');
  if (!input) return;
  const status = document.querySelector('#verify-result');
  const expected = [...document.querySelectorAll('[data-sha256]')];
  document.querySelector('#file-check-control').hidden = false;
  let operation = 0;
  input.addEventListener('change', async () => {
    const current = ++operation;
    const file = input.files[0];
    if (!file) { status.textContent = 'Aguardando a escolha de um arquivo.'; return; }
    if (file.size > 5000000) { status.textContent = 'Escolha um PDF de até 5 MB. Todos os PDFs desta edição são menores que esse limite.'; return; }
    status.textContent = 'Conferindo o arquivo neste dispositivo…';
    try {
      const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
      if (current !== operation) return;
      const hash = [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
      const match = expected.find(entry => entry.dataset.sha256 === hash);
      status.textContent = match ? `Conferido: “${file.name}” corresponde exatamente a ${match.dataset.file} desta edição.` : `“${file.name}” não corresponde aos PDFs desta edição. Confira se escolheu o arquivo correto ou baixe uma nova cópia na lista abaixo. Isso, sozinho, não identifica a causa da diferença.`;
    } catch {
      if (current === operation) status.textContent = 'Não foi possível conferir neste navegador. Tente novamente ou use as instruções de conferência manual abaixo.';
    }
  });
})();
