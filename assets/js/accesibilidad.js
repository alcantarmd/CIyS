/* ===============================================================
   Preferencias de visualización

   Importante: esto NO es lo que hace accesible al sitio. La norma se
   cumple en el HTML, en el contraste de los tokens y en el manejo del
   foco. Este panel agrega comodidad para quien la necesite; si nadie
   lo abre, el sitio sigue cumpliendo igual.

   Las preferencias se guardan solo en el navegador de quien visita.
   No se envían a ninguna parte.
   =============================================================== */

(function () {
  "use strict";

  var RAIZ = document.documentElement;
  var LLAVE = "cis-preferencias";

  var AJUSTES = {
    tema:       { attr: "data-tema",       valores: ["auto", "claro", "oscuro"],                   porOmision: "auto" },
    texto:      { attr: "data-texto",      valores: ["normal", "grande", "mayor", "maximo"],       porOmision: "normal" },
    contraste:  { attr: "data-contraste",  valores: ["normal", "alto"],                            porOmision: "normal" },
    subrayado:  { attr: "data-subrayado",  valores: ["no", "si"],                                  porOmision: "no" }
  };

  var estado = leer();

  function leer() {
    var base = {};
    Object.keys(AJUSTES).forEach(function (k) { base[k] = AJUSTES[k].porOmision; });
    try {
      var crudo = window.localStorage.getItem(LLAVE);
      if (crudo) {
        var guardado = JSON.parse(crudo);
        Object.keys(AJUSTES).forEach(function (k) {
          if (AJUSTES[k].valores.indexOf(guardado[k]) !== -1) base[k] = guardado[k];
        });
      }
    } catch (e) { /* modo privado o almacenamiento bloqueado: se usan los valores por omisión */ }
    return base;
  }

  function guardar() {
    try { window.localStorage.setItem(LLAVE, JSON.stringify(estado)); } catch (e) { /* sin persistencia */ }
  }

  var consultaOscura = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function aplicar() {
    Object.keys(AJUSTES).forEach(function (k) {
      RAIZ.setAttribute(AJUSTES[k].attr, estado[k]);
    });
    // El CSS necesita saber si "auto" está resolviendo a oscuro.
    var autoOscuro = estado.tema === "auto" && consultaOscura && consultaOscura.matches;
    RAIZ.classList.toggle("oscuro-sistema", !!autoOscuro);
  }

  if (consultaOscura) {
    var alCambiarSistema = function () { if (estado.tema === "auto") aplicar(); };
    if (consultaOscura.addEventListener) consultaOscura.addEventListener("change", alCambiarSistema);
    else if (consultaOscura.addListener) consultaOscura.addListener(alCambiarSistema);
  }

  aplicar();

  /* ------------------------------------------------ interfaz del panel */

  var boton = document.getElementById("btn-accesibilidad");
  var panel = document.getElementById("panel-accesibilidad");
  var aviso = document.getElementById("aviso-accesibilidad");
  if (!boton || !panel) return;

  function anunciar(texto) {
    if (aviso) aviso.textContent = texto;
  }

  function marcarBotones() {
    var botones = panel.querySelectorAll("[data-ajuste]");
    Array.prototype.forEach.call(botones, function (b) {
      var clave = b.getAttribute("data-ajuste");
      var valor = b.getAttribute("data-valor");
      b.setAttribute("aria-pressed", estado[clave] === valor ? "true" : "false");
    });
  }

  function fijar(clave, valor, etiqueta) {
    if (!AJUSTES[clave] || AJUSTES[clave].valores.indexOf(valor) === -1) return;
    estado[clave] = valor;
    aplicar();
    guardar();
    marcarBotones();
    anunciar(etiqueta + " aplicado.");
  }

  panel.addEventListener("click", function (ev) {
    var b = ev.target.closest("[data-ajuste]");
    if (!b) return;
    fijar(b.getAttribute("data-ajuste"), b.getAttribute("data-valor"), b.getAttribute("data-etiqueta") || b.textContent.trim());
  });

  var restablecer = document.getElementById("restablecer-accesibilidad");
  if (restablecer) {
    restablecer.addEventListener("click", function () {
      Object.keys(AJUSTES).forEach(function (k) { estado[k] = AJUSTES[k].porOmision; });
      aplicar();
      guardar();
      marcarBotones();
      anunciar("Preferencias restablecidas.");
    });
  }

  function abrir() {
    panel.hidden = false;
    boton.setAttribute("aria-expanded", "true");
    var primero = panel.querySelector("button");
    if (primero) primero.focus();
    document.addEventListener("keydown", alPresionarTecla, true);
    document.addEventListener("click", alClicFuera, true);
  }

  function cerrar(devolverFoco) {
    panel.hidden = true;
    boton.setAttribute("aria-expanded", "false");
    document.removeEventListener("keydown", alPresionarTecla, true);
    document.removeEventListener("click", alClicFuera, true);
    if (devolverFoco) boton.focus();
  }

  function alPresionarTecla(ev) {
    if (ev.key === "Escape") { ev.stopPropagation(); cerrar(true); return; }
    if (ev.key !== "Tab") return;
    // El foco no debe escaparse del panel mientras está abierto.
    var focoables = panel.querySelectorAll("button, [href], input, select, textarea");
    if (!focoables.length) return;
    var primero = focoables[0];
    var ultimo = focoables[focoables.length - 1];
    if (ev.shiftKey && document.activeElement === primero) { ev.preventDefault(); ultimo.focus(); }
    else if (!ev.shiftKey && document.activeElement === ultimo) { ev.preventDefault(); primero.focus(); }
  }

  function alClicFuera(ev) {
    if (panel.contains(ev.target) || boton.contains(ev.target)) return;
    cerrar(false);
  }

  boton.addEventListener("click", function () {
    if (panel.hidden) abrir(); else cerrar(true);
  });

  marcarBotones();
})();
