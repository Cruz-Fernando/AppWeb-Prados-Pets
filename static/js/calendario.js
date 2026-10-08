/* HU08 · Calendario visual — interacciones y animaciones */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var cal = document.getElementById("cal");
  var scroller = document.getElementById("cal-scroll");
  if (!cal) return;

  var horaInicio = parseInt(cal.dataset.horaInicio, 10);
  var horaFin = parseInt(cal.dataset.horaFin, 10);
  var totalMin = (horaFin - horaInicio) * 60;

  /* ── 1. Contadores animados ─────────────────────────── */
  document.querySelectorAll(".cal-count").forEach(function (el, i) {
    var to = parseInt(el.dataset.to, 10) || 0;
    if (reduceMotion || to === 0) { el.textContent = to; return; }
    var dur = 900, start = null, delay = 250 + i * 80;
    function tick(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(to * eased);
      if (p < 1) requestAnimationFrame(tick);
    }
    setTimeout(function () { requestAnimationFrame(tick); }, delay);
  });

  /* ── 2. Línea de la hora actual ───────────────────── */
  var nowLine = document.getElementById("cal-now");
  var nowLabel = document.getElementById("cal-now-label");
  function fmtHora(d) {
    var h = d.getHours(), m = d.getMinutes();
    var h12 = h % 12 === 0 ? 12 : h % 12;
    return h12 + ":" + (m < 10 ? "0" : "") + m;
  }
  function updateNow() {
    if (!nowLine) return null;
    var d = new Date();
    var mins = d.getHours() * 60 + d.getMinutes() - horaInicio * 60;
    if (mins < 0 || mins > totalMin) { nowLine.hidden = nowLabel.hidden = true; return null; }
    var top = (100 * mins / totalMin) + "%";
    nowLine.hidden = nowLabel.hidden = false;
    nowLine.style.top = top;
    nowLabel.style.top = top;
    nowLabel.textContent = fmtHora(d);
    nowLabel.title = "Hora actual";
    return mins;
  }
  var nowMins = updateNow();
  setInterval(updateNow, 30000);

  /* ── 3. Auto-scroll a la hora actual o a la primera cita ─ */
  function autoScroll() {
    if (!scroller || scroller.scrollHeight <= scroller.clientHeight) return;
    var col = cal.querySelector(".cal-col");
    if (!col) return;
    var colH = col.offsetHeight;
    var headH = cal.querySelector(".cal-dayhead").offsetHeight;
    var targetMin = nowMins;
    if (targetMin === null) {
      var first = null;
      cal.querySelectorAll(".cal-event").forEach(function (ev) {
        var t = parseFloat(ev.style.top);
        if (first === null || t < first) first = t;
      });
      if (first === null) return;
      targetMin = first / 100 * totalMin;
    }
    var y = headH + colH * (targetMin / totalMin) - scroller.clientHeight / 3;
    scroller.scrollTo({ top: Math.max(0, y), behavior: reduceMotion ? "auto" : "smooth" });
  }
  setTimeout(autoScroll, reduceMotion ? 0 : 700);

  /* ── 4. Filtros por tipo de servicio ────────────────── */
  document.querySelectorAll(".cal-filter").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var on = !btn.classList.contains("is-on");
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      var cat = btn.dataset.filter;
      cal.querySelectorAll('.cal-event[data-categoria="' + cat + '"]').forEach(function (ev, i) {
        ev.style.transitionDelay = (i * 25) + "ms";
        ev.classList.toggle("is-hidden", !on);
        ev.tabIndex = on ? 0 : -1;
      });
    });
  });

  /* ── 5. Modal de detalle ──────────────────────────── */
  var modal = document.getElementById("cal-modal");
  var card = modal.querySelector(".cal-modal__card");
  var lastFocus = null;
  var etiquetas = { consulta: "Consulta médica", peluqueria: "Peluquería y Spa", cancelada: "Cancelada" };

  function set(id, txt) { document.getElementById(id).textContent = txt; }

  function openModal(ev) {
    var d = ev.dataset;
    var cat = d.categoria;
    card.dataset.cat = cat;
    set("cal-modal-chip", etiquetas[cat] || cat);
    set("cal-modal-title", d.titulo);
    set("cal-modal-service", d.servicio);
    set("cal-modal-fecha", d.fecha);
    set("cal-modal-horario", d.horario);
    var min = parseInt(d.duracion, 10);
    set("cal-modal-duracion", min >= 60 ? (Math.floor(min / 60) + " h" + (min % 60 ? " " + (min % 60) + " min" : "")) : min + " min");
    set("cal-modal-estado", d.estado);
    var esRaza = d.responsable.indexOf("Raza:") === 0;
    set("cal-modal-resp-label", esRaza ? "Raza" : "Veterinario(a)");
    set("cal-modal-resp", esRaza ? d.responsable.replace("Raza: ", "") : d.responsable);

    lastFocus = ev;
    modal.classList.remove("is-closing");
    modal.hidden = false;
    // Reiniciar animaciones internas
    card.style.animation = "none"; void card.offsetWidth; card.style.animation = "";
    modal.querySelector(".cal-modal__close").focus();
  }

  function closeModal() {
    if (modal.hidden) return;
    if (reduceMotion) { modal.hidden = true; if (lastFocus) lastFocus.focus(); return; }
    modal.classList.add("is-closing");
    setTimeout(function () {
      modal.hidden = true;
      modal.classList.remove("is-closing");
      if (lastFocus) lastFocus.focus();
    }, 240);
  }

  cal.addEventListener("click", function (e) {
    var ev = e.target.closest(".cal-event");
    if (ev) openModal(ev);
  });
  modal.addEventListener("click", function (e) {
    if (e.target.closest("[data-close]")) closeModal();
  });

  /* ── 6. Efecto "spotlight" que sigue al mouse ───────── */
  if (!reduceMotion) {
    cal.addEventListener("pointermove", function (e) {
      var ev = e.target.closest(".cal-event");
      if (!ev) return;
      var r = ev.getBoundingClientRect();
      ev.style.setProperty("--mx", (e.clientX - r.left) + "px");
      ev.style.setProperty("--my", (e.clientY - r.top) + "px");
    });
  }

  /* ── 7. Atajos de teclado ─────────────────────────── */
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeModal(); return; }
    if (!modal.hidden) return;
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select" || e.metaKey || e.ctrlKey || e.altKey) return;

    var link = null;
    if (e.key === "ArrowLeft") link = document.querySelector('[data-key="ArrowLeft"]');
    else if (e.key === "ArrowRight") link = document.querySelector('[data-key="ArrowRight"]');
    else if (e.key === "t" || e.key === "T") link = document.querySelector(".cal-today-btn");
    else if (e.key === "d" || e.key === "D") link = document.querySelectorAll(".cal-switch__opt")[0];
    else if (e.key === "s" || e.key === "S") link = document.querySelectorAll(".cal-switch__opt")[1];
    if (link) { e.preventDefault(); link.click(); }
  });

  /* ── 8. Deslizar la píldora del selector Día/Semana ─── */
  var sw = document.querySelector(".cal-switch");
  if (sw) {
    sw.querySelectorAll(".cal-switch__opt").forEach(function (opt, i) {
      opt.addEventListener("click", function () {
        sw.dataset.active = i === 0 ? "dia" : "semana";
      });
    });
  }
})();
