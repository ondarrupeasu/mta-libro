// Panel de edición de fotos (Fase 4).
// Sitio estático: los reemplazos se guardan en localStorage del navegador para
// previsualizar, y se pueden exportar a JSON para hacerlos permanentes en el proyecto.
(() => {
  const LS = 'mta-photo:';
  const key = (orig) => LS + orig;

  // aplica overrides guardados
  function applyOverrides() {
    document.querySelectorAll('figure img').forEach(img => {
      const orig = img.getAttribute('data-orig') || img.getAttribute('src');
      img.setAttribute('data-orig', orig);
      const ov = localStorage.getItem(key(orig));
      if (ov) {
        img.src = ov;
        img.closest('figure').classList.add('edited');
      }
    });
  }

  function pickFile(img) {
    const orig = img.getAttribute('data-orig');
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = 'image/*';
    inp.onchange = () => {
      const file = inp.files[0];
      if (!file) return;
      const r = new FileReader();
      r.onload = () => {
        try {
          localStorage.setItem(key(orig), r.result);
          img.src = r.result;
          img.closest('figure').classList.add('edited');
          refreshPanel();
        } catch (e) {
          alert('The image is too large for the browser store. Try a smaller/compressed file.');
        }
      };
      r.readAsDataURL(file);
    };
    inp.click();
  }

  function revert(orig) {
    localStorage.removeItem(key(orig));
    document.querySelectorAll('figure img').forEach(img => {
      if (img.getAttribute('data-orig') === orig) {
        img.src = orig;
        img.closest('figure').classList.remove('edited');
      }
    });
    refreshPanel();
  }

  function allOverrides() {
    const out = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k.startsWith(LS)) out.push({ path: k.slice(LS.length), data: localStorage.getItem(k) });
    }
    return out;
  }

  function refreshPanel() {
    const list = document.getElementById('edits-list');
    if (!list) return;
    const ov = allOverrides();
    document.getElementById('edits-count').textContent = ov.length;
    if (!ov.length) { list.innerHTML = '<p class="muted">No photo edits yet. Turn on edit mode and use “swap” under any figure.</p>'; return; }
    list.innerHTML = ov.map(o =>
      `<div class="edit-row"><img src="${o.data}" alt=""><code>${o.path}</code>` +
      `<button data-revert="${o.path}">revert</button></div>`).join('');
    list.querySelectorAll('[data-revert]').forEach(b =>
      b.onclick = () => revert(b.getAttribute('data-revert')));
  }

  function exportJSON() {
    const ov = allOverrides();
    if (!ov.length) { alert('No photo edits to export yet.'); return; }
    const map = {};
    ov.forEach(o => map[o.path] = o.data);
    const blob = new Blob([JSON.stringify(map, null, 1)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'mta-photo-overrides.json';
    a.click();
  }

  // ---- Publicar directamente en GitHub (Pages reconstruye solo) ----
  const REPO = { owner: 'ondarrupeasu', repo: 'mta-libro', branch: 'main' };
  const TOKEN_KEY = 'mta-gh-token';
  const getToken = () => localStorage.getItem(TOKEN_KEY) || '';

  function setToken() {
    const cur = getToken();
    const t = prompt(
      'Paste your GitHub token (fine-grained, repo "mta-libro", Contents: Read and write).\n' +
      'It is stored only in this browser and only talks to GitHub. Leave empty to remove.',
      cur);
    if (t === null) return;
    if (t.trim()) localStorage.setItem(TOKEN_KEY, t.trim());
    else localStorage.removeItem(TOKEN_KEY);
    updateTokenUi();
  }

  function updateTokenUi() {
    const b = document.getElementById('edits-token');
    const pub = document.getElementById('edits-publish');
    if (b) b.textContent = getToken() ? '🔑 Token set' : 'Set GitHub token…';
    if (pub) pub.disabled = !getToken();
  }

  async function gh(path, opts = {}) {
    const res = await fetch('https://api.github.com/repos/' + REPO.owner + '/' + REPO.repo + path, {
      ...opts,
      headers: {
        'Authorization': 'Bearer ' + getToken(),
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        ...(opts.headers || {})
      }
    });
    return res;
  }

  async function getSha(repoPath) {
    const r = await gh('/contents/' + encodeURI(repoPath) + '?ref=' + REPO.branch);
    if (r.status === 200) { const j = await r.json(); return j.sha; }
    return null; // no existe todavía
  }

  async function putFile(repoPath, b64content, message) {
    const sha = await getSha(repoPath);
    const body = { message, content: b64content, branch: REPO.branch };
    if (sha) body.sha = sha;
    const r = await gh('/contents/' + encodeURI(repoPath), { method: 'PUT', body: JSON.stringify(body) });
    if (!r.ok) throw new Error(repoPath + ' → HTTP ' + r.status + ' ' + (await r.text()).slice(0, 140));
    return r.json();
  }

  const b64 = (str) => btoa(unescape(encodeURIComponent(str)));

  async function publish() {
    if (!getToken()) { setToken(); return; }
    const ov = allOverrides();
    const status = document.getElementById('pub-status');
    if (!ov.length) { status.textContent = 'No photo edits to publish.'; return; }
    if (!confirm('Publish ' + ov.length + ' photo change(s) to the live website?')) return;

    const pub = document.getElementById('edits-publish');
    pub.disabled = true;
    try {
      // 1) cada imagen reemplaza su fichero en docs/img/...
      for (let i = 0; i < ov.length; i++) {
        const o = ov[i];
        status.textContent = 'Publishing image ' + (i + 1) + '/' + ov.length + '…';
        const b64data = o.data.split(',')[1];               // quita "data:image/..;base64,"
        await putFile('docs/' + o.path, b64data, 'Replace photo ' + o.path + ' via web editor');
      }
      // 2) actualiza photo-overrides.json (para que los rebuilds locales lo conserven)
      status.textContent = 'Updating photo-overrides.json…';
      let existing = {};
      const cur = await gh('/contents/photo-overrides.json?ref=' + REPO.branch);
      if (cur.status === 200) {
        const j = await cur.json();
        try { existing = JSON.parse(decodeURIComponent(escape(atob(j.content.replace(/\n/g, ''))))); } catch (e) {}
      }
      ov.forEach(o => existing[o.path] = o.data);
      await putFile('photo-overrides.json', b64(JSON.stringify(existing, null, 1)), 'Update photo overrides via web editor');

      status.innerHTML = '✅ Published. The website updates in about a minute (refresh then).';
    } catch (e) {
      status.innerHTML = '⚠️ ' + (e.message || e);
    } finally {
      pub.disabled = false;
    }
  }

  // wiring
  document.addEventListener('DOMContentLoaded', () => {
    applyOverrides();   // aplica reemplazos locales (previsualización del curador)

    // La edición sólo se habilita en modo privado (…/unitX.html?edit).
    // En la web pública no aparece ningún control de edición.
    const editMode = /(?:^|[?&])edit(?:=|&|$)/.test(location.search);
    if (!editMode) return;
    document.body.classList.add('editmode');

    const toggle = document.getElementById('editToggle');
    if (toggle) toggle.addEventListener('click', () => {
      document.body.classList.toggle('editing');
      toggle.classList.toggle('on');
      const on = document.body.classList.contains('editing');
      toggle.textContent = on ? '✓ Editing photos' : '✎ Edit photos';
      const panel = document.getElementById('edits-panel');
      if (panel) panel.style.display = on ? 'block' : 'none';
      if (on) refreshPanel();
    });

    document.querySelectorAll('.swap').forEach(btn => {
      btn.addEventListener('click', () => {
        const fig = btn.closest('figure');
        pickFile(fig.querySelector('img'));
      });
    });

    const ex = document.getElementById('edits-export');
    if (ex) ex.addEventListener('click', exportJSON);

    const tk = document.getElementById('edits-token');
    if (tk) tk.addEventListener('click', setToken);
    const pb = document.getElementById('edits-publish');
    if (pb) pb.addEventListener('click', publish);
    updateTokenUi();
  });
})();
