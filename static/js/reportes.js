/**
 * Reporte semanal: cambiar de semana al elegirla y tooltip de las gráficas.
 *
 * Cada marca de una gráfica lleva su texto en data-tip. El tooltip solo
 * repite lo que ya está en la gráfica o en su tabla de datos (nunca es la
 * única forma de leer un valor) y aparece igual con el mouse o con el teclado.
 */
(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('rep-semana-form');
    if (form) {
      var boton = form.querySelector('.rep-semana__ver');
      if (boton) boton.style.display = 'none';
      form.querySelector('select').addEventListener('change', function () {
        if (form.requestSubmit) form.requestSubmit(); else form.submit();
      });
    }

    var tip = document.getElementById('graf-tip');
    if (!tip) return;

    function colocar(x, y) {
      var caja = tip.getBoundingClientRect();
      var izquierda = Math.min(Math.max(8, x + 14), window.innerWidth - caja.width - 8);
      var arriba = y - caja.height - 12;
      if (arriba < 8) arriba = y + 18;
      tip.style.left = izquierda + 'px';
      tip.style.top = arriba + 'px';
    }

    function mostrar(elemento, x, y) {
      tip.textContent = elemento.getAttribute('data-tip');   // texto plano, nunca HTML
      tip.hidden = false;
      colocar(x, y);
    }

    function ocultar() { tip.hidden = true; }

    document.addEventListener('pointermove', function (e) {
      var elemento = e.target.closest && e.target.closest('[data-tip]');
      if (elemento) mostrar(elemento, e.clientX, e.clientY); else ocultar();
    });

    document.addEventListener('focusin', function (e) {
      var elemento = e.target.closest && e.target.closest('[data-tip]');
      if (!elemento) return;
      var caja = elemento.getBoundingClientRect();
      mostrar(elemento, caja.left + caja.width / 2, caja.top);
    });

    document.addEventListener('focusout', ocultar);
    window.addEventListener('scroll', ocultar, { passive: true });
  });
})();
