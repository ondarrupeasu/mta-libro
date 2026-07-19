// Modo claro/oscuro (sol/luna), recuerda la elección en el navegador.
(function () {
  var root = document.documentElement;
  function paintIcon() {
    var dark = root.getAttribute('data-theme') === 'dark';
    var el = document.getElementById('theme-icon');
    if (el) el.innerHTML = dark ? '&#9789;' : '&#9728;';   // ☾ / ☀
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
