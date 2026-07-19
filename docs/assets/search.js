// Buscador ligero client-side sobre los titulos de seccion del libro.
(async () => {
  const q = document.getElementById('q');
  const box = document.getElementById('results');
  if (!q) return;
  let idx = [];
  try {
    idx = await (await fetch('assets/search-index.json')).json();
  } catch (e) { return; }

  function render(list) {
    if (!list.length) { box.innerHTML = ''; return; }
    box.innerHTML = list.slice(0, 12).map(r =>
      `<a href="${r.u}.html#${r.a}"><span class="u">Unit ${r.u.replace('unit','')} · ${r.title}</span><br>${r.t}</a>`
    ).join('');
  }

  q.addEventListener('input', () => {
    const s = q.value.trim().toLowerCase();
    if (s.length < 2) { box.innerHTML = ''; return; }
    const hits = idx.filter(r => r.t.toLowerCase().includes(s));
    render(hits);
  });
})();
