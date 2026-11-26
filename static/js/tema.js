/**
 * Prados Pets: interruptor de modo día / noche.
 *
 * El modo inicial lo fija un script en el <head> de base.html (antes de pintar).
 * Aquí solo se atienden los clics en el interruptor, se guarda la elección en
 * este navegador y, mientras nadie elija, se sigue el modo del sistema.
 */
(function () {
  var raiz = document.documentElement;
  var CLAVE = 'pp-tema';

  function guardado() {
    try { return localStorage.getItem(CLAVE); } catch (e) { return null; }
  }

  function marcarBotones(tema) {
    document.querySelectorAll('[data-tema-op]').forEach(function (boton) {
      boton.setAttribute('aria-pressed', String(boton.getAttribute('data-tema-op') === tema));
    });
  }

  function aplicar(tema) {
    raiz.setAttribute('data-tema', tema);
    marcarBotones(tema);
  }

  function cambiar(tema) {
    if (tema === raiz.getAttribute('data-tema')) return;
    try { localStorage.setItem(CLAVE, tema); } catch (e) {}
    var sinMovimiento = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    // Fundido corto entre modos donde el navegador lo permite.
    if (document.startViewTransition && !sinMovimiento) {
      document.startViewTransition(function () { aplicar(tema); });
    } else {
      aplicar(tema);
    }
  }

  document.addEventListener('click', function (evento) {
    var boton = evento.target.closest('[data-tema-op]');
    if (boton) cambiar(boton.getAttribute('data-tema-op'));
  });

  // Mientras la persona no haya elegido, acompaña el cambio del sistema.
  var oscuro = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  if (oscuro && oscuro.addEventListener) {
    oscuro.addEventListener('change', function (e) {
      if (!guardado()) aplicar(e.matches ? 'noche' : 'dia');
    });
  }

  // Otra pestaña cambió el modo: se replica aquí.
  window.addEventListener('storage', function (e) {
    if (e.key === CLAVE && (e.newValue === 'dia' || e.newValue === 'noche')) aplicar(e.newValue);
  });

  document.addEventListener('DOMContentLoaded', function () {
    marcarBotones(raiz.getAttribute('data-tema') || 'dia');
  });
})();
