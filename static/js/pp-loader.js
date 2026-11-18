/**
 * Prados Pets — Pantalla de carga con el logo.
 *
 * - Al abrir una página, el <html> trae la clase «pp-cargando» y aquí se quita
 *   en cuanto el contenido está listo.
 * - Al hacer clic en un enlace interno o enviar un formulario, la pantalla
 *   aparece mientras el servidor responde. Solo se muestra si la espera pasa
 *   de RETARDO ms, para que las respuestas rápidas no parpadeen.
 * - No se muestra en descargas (PDF, Excel, adjuntos), enlaces que abren otra
 *   pestaña ni en elementos con el atributo data-sin-carga.
 *
 * Uso manual desde otros scripts: window.ppCarga.mostrar() / .ocultar()
 */
(function () {
  'use strict';

  var html = document.documentElement;
  var RETARDO = 150;     // ms antes de mostrar la pantalla
  var LIMITE = 15000;    // ms: se retira sola si nada pasa (p. ej., una descarga no detectada)
  var DESCARGA = /(\/pdf\/|exportar|descargar|comprobante|\/media\/|\.(pdf|xlsx?|csv|zip)(\?|$))/i;
  var tMostrar = null;
  var tLimite = null;

  function ocultar() {
    clearTimeout(tMostrar);
    clearTimeout(tLimite);
    html.classList.remove('pp-cargando');
  }

  function mostrar(evento) {
    clearTimeout(tMostrar);
    tMostrar = setTimeout(function () {
      // Si otro script canceló la navegación (preventDefault), no se muestra.
      if (evento && evento.defaultPrevented) return;
      html.classList.add('pp-cargando');
      clearTimeout(tLimite);
      tLimite = setTimeout(ocultar, LIMITE);
    }, RETARDO);
  }

  window.ppCarga = { mostrar: mostrar, ocultar: ocultar };

  // Página nueva: se retira la pantalla cuando el DOM está listo.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ocultar);
  } else {
    ocultar();
  }

  // Volver con «Atrás»: el navegador restaura la página tal como quedó (con la
  // pantalla visible), así que hay que retirarla.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) ocultar();
  });

  function esDescarga(url) {
    return DESCARGA.test(url.pathname + url.search);
  }

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var enlace = e.target.closest && e.target.closest('a[href]');
    if (!enlace || enlace.hasAttribute('download') || enlace.hasAttribute('data-sin-carga')) return;
    if (enlace.target && enlace.target !== '_self') return;

    var href = enlace.getAttribute('href');
    if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) return;

    var url = new URL(enlace.href, location.href);
    if (url.origin !== location.origin || esDescarga(url)) return;
    // Ancla dentro de la misma página: no hay navegación.
    if (url.pathname === location.pathname && url.search === location.search && url.hash) return;

    mostrar(e);
  });

  document.addEventListener('submit', function (e) {
    var form = e.target;
    var boton = e.submitter;
    if (form.hasAttribute('data-sin-carga') || (boton && boton.hasAttribute('data-sin-carga'))) return;

    var destino = (boton && boton.getAttribute('formtarget')) || form.getAttribute('target');
    if (destino && destino !== '_self') return;

    var accion = (boton && boton.getAttribute('formaction')) || form.getAttribute('action') || location.href;
    if (esDescarga(new URL(accion, location.href))) return;

    mostrar(e);
  });
})();
