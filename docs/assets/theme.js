// Modo claro/oscuro (sol/luna), recuerda la elección en el navegador.
(function () {
  var root = document.documentElement;
  // luna creciente rellena e inclinada (tipo bandera), y sol de rayos
  var MOON = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"'
    + ' style="transform:rotate(-18deg)"><path fill="currentColor"'
    + ' d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>';
  var SUN = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none"'
    + ' stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">'
    + '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
    + 'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  function paintIcon() {
    var dark = root.getAttribute('data-theme') === 'dark';
    var el = document.getElementById('theme-icon');
    if (el) el.innerHTML = dark ? MOON : SUN;
  }
  document.addEventListener('DOMContentLoaded', function () {
    paintIcon();
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('mta-theme', next); } catch (e) {}
      paintIcon();
    });
  });
})();
