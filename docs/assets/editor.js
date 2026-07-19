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
  });
})();
