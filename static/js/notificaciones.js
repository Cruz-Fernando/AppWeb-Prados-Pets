/**
 * Prados Pets — Campana de notificaciones y mensajes flash.
 *
 * Campana: después de cargar la página pide /notificaciones/ (no frena la
 * pantalla), muestra la burbuja con lo pendiente y se refresca cada 5 minutos
 * mientras la pestaña está visible. «✓ Avisé» se envía sin recargar.
 *
 * Mensajes flash (.app-messages__item): botón para cerrarlos; los de éxito e
 * información se van solos a los pocos segundos. Los errores se quedan.
 */
(function () {
  'use strict';

  var REFRESCO = 5 * 60 * 1000;

  function iniciarCampana() {
    var raiz = document.getElementById('notif');
    if (!raiz) return;
    var boton = document.getElementById('notif-boton');
    var panel = document.getElementById('notif-panel');
    var burbuja = document.getElementById('notif-burbuja');
    var etiqueta = document.getElementById('notif-etiqueta');
    var url = raiz.dataset.url;
    var ultimaCarga = 0;
    var cargando = false;

    function pintarTotal(total) {
      burbuja.hidden = !total;
      burbuja.textContent = total > 99 ? '99+' : String(total);
      boton.classList.toggle('tiene-pendientes', total > 0);
      etiqueta.textContent = total
        ? 'Notificaciones: ' + total + ' por atender'
        : 'Notificaciones: nada pendiente';
    }

    function cargar() {
      if (cargando) return;
      cargando = true;
      fetch(url, { headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.text() : Promise.reject(r.status); })
        .then(function (html) {
          panel.innerHTML = html;
          var contenido = panel.querySelector('[data-total]');
          pintarTotal(contenido ? parseInt(contenido.dataset.total, 10) || 0 : 0);
          ultimaCarga = Date.now();
        })
        .catch(function () {
          if (!ultimaCarga) panel.innerHTML = '<p class="notif-vacio" id="notif-titulo">No se pudieron cargar las notificaciones.</p>';
        })
        .finally(function () { cargando = false; });
    }

    function abrir() {
      panel.hidden = false;
      boton.setAttribute('aria-expanded', 'true');
      // Si el contenido tiene más de un minuto, se actualiza al abrir.
      if (Date.now() - ultimaCarga > 60 * 1000) cargar();
    }

    function cerrar(devolverFoco) {
      if (panel.hidden) return;
      panel.hidden = true;
      boton.setAttribute('aria-expanded', 'false');
      if (devolverFoco) boton.focus();
    }

    boton.addEventListener('click', function (e) {
      e.stopPropagation();
      if (panel.hidden) abrir(); else cerrar(false);
    });
    document.addEventListener('click', function (e) {
      if (!raiz.contains(e.target)) cerrar(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') cerrar(true);
    });

    // «✓ Avisé» sin recargar la página
    panel.addEventListener('submit', function (e) {
      var form = e.target.closest('.js-notif-avisado');
      if (!form) return;
      e.preventDefault();
      var btn = form.querySelector('button');
      btn.disabled = true;
      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'fetch' },
        credentials: 'same-origin',
      })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
        .then(function () {
          var item = form.closest('.notif-item');
          if (item) item.classList.add('is-hecho');
          // En la pantalla de recordatorios también hay que reflejarlo.
          if (document.getElementById('recordatorios-por-avisar')) {
            window.location.reload();
          } else {
            cargar();
          }
        })
        .catch(function () { form.submit(); });
    });

    cargar();
    setInterval(function () {
      if (document.visibilityState === 'visible') cargar();
    }, REFRESCO);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible' && Date.now() - ultimaCarga > REFRESCO) cargar();
    });
  }

  function iniciarMensajes() {
    document.querySelectorAll('.app-messages__item').forEach(function (item) {
      if (item.querySelector('.app-messages__cerrar')) return;
      var cerrar = document.createElement('button');
      cerrar.type = 'button';
      cerrar.className = 'app-messages__cerrar';
      cerrar.setAttribute('aria-label', 'Cerrar mensaje');
      cerrar.innerHTML = '&times;';
      item.appendChild(cerrar);

      function quitar() {
        item.classList.add('is-saliendo');
        setTimeout(function () {
          var lista = item.parentElement;
          item.remove();
          if (lista && !lista.children.length) lista.remove();
        }, 300);
      }
      cerrar.addEventListener('click', quitar);

      var esError = /--(error|warning)\b/.test(item.className);
      if (!esError) {
        var t = setTimeout(quitar, 7000);
        // Si la persona está leyendo (pasa el mouse o enfoca), no se va.
        item.addEventListener('mouseenter', function () { clearTimeout(t); });
        item.addEventListener('focusin', function () { clearTimeout(t); });
      }
    });
  }

  function iniciar() {
    iniciarCampana();
    iniciarMensajes();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
