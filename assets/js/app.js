/* ===============================================================
   Central de Iniciativas y Servicios
   Facultad de Medicina, Universidad de Chile

   MVP: solo servicios. Las iniciativas entran en una fase posterior.

   Navegación por hash, para que cada ficha tenga una URL propia que
   se pueda pegar en un correo y sobreviva al botón "atrás":
     #/                         portada
     #/estamento/academico      un estamento
     #/servicio/<slug>          una ficha
     #/interno                  vista interna de cobertura
     #/interno/<direccion>
   =============================================================== */

const SERVICIOS = window.SERVICIOS || [];

const DIRS = {
  academica: "Dirección Académica",
  investigacion: "Investigación e Innovación",
  degi: "DEGI",
  dri: "Relaciones Internacionales",
  digen: "Igualdad de Género",
  daec: "Asuntos Estudiantiles",
  pregrado: "Dirección de Pregrado",
  nivel_central: "Universidad de Chile, nivel central",
  clinica: "Dirección Clínica",
  extension: "Dirección de Extensión",
  postgrado: "Escuela de Postgrado",
  decanato: "Decanato",
  otro: "Sin dirección"
};

const SOLICITANTES = {
  academico: "Académicos", docente: "Docentes", estudiante: "Estudiantes",
  estudiante_pregrado: "Estudiantes de pregrado", estudiante_postgrado: "Estudiantes de postgrado",
  funcionario: "Funcionarios", unidad_academica: "Unidades académicas",
  autoridad_unidad: "Directores/as de unidad", direccion: "Direcciones",
  grupo_investigacion: "Equipos de investigación", externo: "Externos"
};

const VIAS = {
  formulario: "Formulario en línea", plataforma: "Plataforma", correo: "Correo",
  convocatoria: "Convocatoria abierta", presencial: "Atención presencial",
  solicitud_informal: "Solicitud directa", indeterminada: "Sin definir"
};

/* Los tres estamentos. El reparto sale de "quién puede solicitarlo".
   Los servicios dirigidos a una unidad o a una dirección entran en
   académicos, porque quien los pide en nombre de la unidad es su
   director o directora. */
const ESTAMENTOS = {
  academico: {
    titulo: "Académicos y académicas",
    desc: "Docencia, investigación, carrera académica y la gestión de tu unidad.",
    intro: "Incluye lo que se solicita en nombre de un departamento, escuela o instituto, porque quien lo pide es su director o directora.",
    marcador: "acreditación, jerarquización, fondos",
    claves: ["academico", "docente", "autoridad_unidad", "grupo_investigacion", "unidad_academica", "direccion"],
    rutas: [
      { t: "Me toca hacer el PDU de mi unidad", q: ["plan de desarrollo", "autoevaluación", "planificación estratégica"] },
      { t: "Voy a postular a un fondo o proyecto", q: ["financiamiento", "postulación", "presupuesto", "preevaluación", "redacción de proyectos"] },
      { t: "Estoy acreditando mi carrera", q: ["acreditación", "autoevaluación", "programas de curso"] },
      { t: "Quiero mejorar mi docencia", q: ["aprendizaje activo", "evaluaciones", "perfeccionamiento docente", "microcredenciales"] },
      { t: "Necesito jerarquizarme o ascender", q: ["jerarquización", "calificación", "carrera académica", "nombramiento", "concursos"] },
      { t: "Quiero salir o traer a alguien del extranjero", q: ["intercambio", "estadías", "convenios", "movilidad", "doctorados conjuntos", "internacionales"] },
      { t: "Necesito material gráfico o audiovisual", q: ["diagramación", "afiches", "videos", "portadas", "sitios web"] }
    ]
  },
  estudiante: {
    titulo: "Estudiantes",
    desc: "Becas y beneficios, apoyo al aprendizaje, bienestar y movilidad internacional.",
    intro: "Pregrado, postgrado y postítulo.",
    marcador: "beca, intercambio, tutoría",
    claves: ["estudiante", "estudiante_pregrado", "estudiante_postgrado"],
    rutas: [
      { t: "Necesito una beca o un beneficio", q: ["beca", "beneficio", "fondos de ayuda", "seguro", "convocatorias"] },
      { t: "Quiero irme de intercambio", q: ["intercambio", "movilidad", "ayuda de viaje", "estadías", "doctorados conjuntos", "estadas observacionales", "student link"] },
      { t: "Necesito apoyo para estudiar", q: ["tutorías", "ayudantías", "psicoeducativo", "aprendizaje"] },
      { t: "Necesito apoyo en salud o bienestar", q: ["consejería", "salud mental", "seguro de salud", "deportivas"] },
      { t: "Necesito un ajuste por discapacidad", q: ["ajustes razonables", "discapacidad", "equidad", "inclusión"] },
      { t: "Quiero hacer una actividad o postular a un fondo", q: ["iniciativas estudiantiles", "fondo de extensión", "concurso de investigación"] },
      { t: "Necesito aprobación ética para mi investigación", q: ["evaluación ética", "bioética", "protocolos"] },
      { t: "Viví o presencié una situación de acoso", q: ["acoso", "protección", "violencias", "nombre social"] }
    ]
  },
  funcionario: {
    titulo: "Funcionarias y funcionarios",
    desc: "Contrato y remuneraciones, trámites administrativos, bienestar laboral y capacitación.",
    intro: "Personal de colaboración, honorarios y planta.",
    marcador: "honorarios, certificado, capacitación",
    claves: ["funcionario"],
    rutas: [
      { t: "Necesito un certificado o un trámite de personal", q: ["certificados", "atención presencial", "trámites laborales", "solicitudes en línea", "ejecutivas"] },
      { t: "Necesito soporte informático", q: ["mesa de ayuda", "informático", "google", "competencias digitales"] },
      { t: "Tuve un accidente o necesito algo de salud", q: ["accidentes del trabajo", "salud mental", "lactancia"] },
      { t: "Quiero capacitarme", q: ["competencias digitales", "google for education", "diseño educativo"] },
      { t: "Busco un fondo o una convocatoria", q: ["convocatorias", "becas", "financiamiento"] },
      { t: "Viví o presencié una situación de acoso", q: ["acoso", "protección", "violencias", "nombre social"] }
    ]
  }
};

/* ---------------- utilidades ---------------- */
const norm = s => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const $ = id => document.getElementById(id);
const el = (t, c, x) => { const n = document.createElement(t); if (c) n.className = c; if (x !== undefined) n.textContent = x; return n; };
const esc = s => (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

SERVICIOS.forEach(s => {
  s._b = norm(s.n + " " + (s.q || "") + " " + (s.u || "") + " " + DIRS[s.d]);
  s._n = norm(s.n);
});
const PORSLUG = Object.fromEntries(SERVICIOS.map(s => [s.sl, s]));

const deEstamento = k => SERVICIOS.filter(s => (s.s || []).some(x => ESTAMENTOS[k].claves.includes(x)));

let rutaActiva = null;
const consultasVacias = [];

function buscar(t0, base) {
  const t = norm(t0).trim();
  if (!t) return null;
  const term = t.split(/\s+/).filter(Boolean);
  return (base || SERVICIOS).map(s => {
    let p = 0;
    for (const w of term) {
      if (s._n.includes(w)) p += 3;
      else if (s._b.includes(w)) p += 1;
      else return null;
    }
    return { s, p };
  }).filter(Boolean).sort((a, b) => b.p - a.p || a.s.n.localeCompare(b.s.n)).map(x => x.s);
}

function porRuta(r, base) {
  const vistos = new Set(), out = [];
  for (const q of r.q) for (const s of (buscar(q, base) || [])) if (!vistos.has(s.id)) { vistos.add(s.id); out.push(s); }
  return out;
}

/* ---------------- piezas ---------------- */
function tarjeta(s) {
  const a = el("a", "tarjeta");
  a.href = "#/servicio/" + s.sl;
  a.appendChild(el("span", "dir", DIRS[s.d]));
  a.appendChild(el("h3", null, s.n));
  a.appendChild(el("p", null, (s.q || "").length > 130 ? (s.q.slice(0, 130).replace(/\s\S*$/, "") + "…") : s.q));
  if (s.vd) {
    const pie = el("div", "pie");
    pie.appendChild(el("span", "mini ok", VIAS[s.vt]));
    a.appendChild(pie);
  }
  const li = el("li"); li.appendChild(a);
  return li;
}

function pintarGrid(cont, l) {
  cont.innerHTML = "";
  const g = el("ul", "grid");
  l.forEach(s => g.appendChild(tarjeta(s)));
  cont.appendChild(g);
}

function pintarVacio(cont, texto) {
  cont.innerHTML = "";
  const v = el("div", "vacio");
  v.appendChild(el("h3", null, "No encontramos nada para “" + texto + "”"));
  v.appendChild(el("p", null, "Puede que el servicio exista y esté guardado con otro nombre. Es lo más probable: todavía no están cargadas las palabras con que la gente pide cada servicio."));
  const r = el("div", "registrado");
  r.innerHTML = "<b>Tu búsqueda quedó registrada.</b> La lista de lo que nadie encuentra es la agenda de trabajo del catálogo.";
  v.appendChild(r);
  cont.appendChild(v);
}

/* ---------------- portada ---------------- */
function pintarEstamentos() {
  const c = $("estamentos");
  c.innerHTML = "";
  Object.keys(ESTAMENTOS).forEach(k => {
    const e = ESTAMENTOS[k];
    const a = el("a", "est");
    a.href = "#/estamento/" + k;
    a.appendChild(el("h2", null, e.titulo));
    a.appendChild(el("p", "desc", e.desc));
    const ir = el("div", "ir");
    ir.appendChild(el("span", null, "Ver servicios"));
    ir.appendChild(el("span", "fl", "→"));
    a.appendChild(ir);
    const li = el("li"); li.appendChild(a);
    c.appendChild(li);
  });
}

function renderPortada() {
  const t = $("q-portada").value.trim();
  $("limpiar-portada").hidden = !t;
  const c = $("res-portada");
  if (!t) { c.innerHTML = ""; return; }
  const r = buscar(t);
  if (r.length) {
    c.innerHTML = "";
    const bar = el("div", "barra-res");
    bar.appendChild(el("h2", null, "Resultados para “" + t + "”"));
    c.appendChild(bar);
    const g = el("div"); pintarGrid(g, r); c.appendChild(g);
  } else { pintarVacio(c, t); consultasVacias.push(t); }
}

/* ---------------- estamento ---------------- */
let estActual = null;

function abrirEstamento(k) {
  if (!ESTAMENTOS[k]) return irA("#/");
  estActual = k; rutaActiva = null;
  const e = ESTAMENTOS[k], l = deEstamento(k);
  const cab = $("cab-est"); cab.innerHTML = "";
  const b = el("a", "volver");
  b.href = "#/";
  b.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg> Volver a la portada';
  cab.appendChild(b);
  const t = el("div", "tick"); t.appendChild(el("h1", null, e.titulo)); cab.appendChild(t);
  cab.appendChild(el("p", null, e.intro));
  $("q-est").value = "";
  $("q-est").placeholder = e.marcador;
  $("limpiar-est").hidden = true;
  pintarChips();
  $("titulo-res").textContent = "Todos los servicios";
  pintarGrid($("resultados"), l);
  document.title = e.titulo + " · Central de Iniciativas y Servicios";
  mostrar("vista-estamento");
}

function pintarChips() {
  const c = $("chips"); c.innerHTML = "";
  ESTAMENTOS[estActual].rutas.forEach((r, i) => {
    const b = el("button", "chip", r.t);
    b.type = "button";
    b.setAttribute("aria-pressed", rutaActiva === i ? "true" : "false");
    b.addEventListener("click", () => {
      const base = deEstamento(estActual);
      if (rutaActiva === i) {
        rutaActiva = null; pintarChips();
        $("titulo-res").textContent = "Todos los servicios";
        pintarGrid($("resultados"), base);
        return;
      }
      rutaActiva = i; $("q-est").value = ""; $("limpiar-est").hidden = false; pintarChips();
      const l = porRuta(r, base);
      $("titulo-res").textContent = r.t;
      l.length ? pintarGrid($("resultados"), l) : pintarVacio($("resultados"), r.t);
    });
    c.appendChild(b);
  });
}

function renderEstamento() {
  const t = $("q-est").value.trim();
  const base = deEstamento(estActual);
  $("limpiar-est").hidden = !t && rutaActiva === null;
  if (!t) {
    if (rutaActiva === null) {
      $("titulo-res").textContent = "Todos los servicios";
      pintarGrid($("resultados"), base);
    }
    return;
  }
  rutaActiva = null; pintarChips();
  const r = buscar(t, base);
  $("titulo-res").textContent = "Resultados para “" + t + "”";
  if (r.length) pintarGrid($("resultados"), r);
  else { pintarVacio($("resultados"), t); consultasVacias.push(t); }
}

/* ---------------- ficha ---------------- */
function abrirFicha(slug) {
  const s = PORSLUG[slug];
  if (!s) return irA("#/");
  const solicitantes = (s.s || []).map(k => SOLICITANTES[k] || k);
  const esCorreo = s.vd && s.vd.includes("@");
  const contacto = s.cc
    ? (s.cn ? "<b>" + esc(s.cn) + "</b><br>" + esc(s.cc) : esc(s.cc))
    : (s.cn ? "<b>" + esc(s.cn) + "</b><br><span class=\"nulo\">Sin correo registrado</span>" : "<span class=\"nulo\">Sin contacto registrado</span>");

  $("ficha-cont").innerHTML =
    '<div class="ficha">' +
      '<div class="col">' +
        '<div class="encabezado">' +
          '<span class="dir">' + esc(DIRS[s.d]) + '</span>' +
          '<h1>' + esc(s.n) + '</h1>' +
          (s.u ? '<p class="unidad">' + esc(s.u) + '</p>' : '') +
        '</div>' +
        '<p class="entrega">' + esc(s.q) + '</p>' +
        '<div class="bloque">' +
          '<h2 class="rot">Cómo se solicita</h2>' +
          (s.vd
            ? '<a class="cta" href="' + (esCorreo ? "mailto:" + esc(s.vd) : esc(s.vd)) + '"' + (esCorreo ? '' : ' target="_blank" rel="noopener"') + '>' +
              (esCorreo ? "Escribir un correo" : "Abrir " + esc((VIAS[s.vt] || "el sitio").toLowerCase())) + '</a>' +
              '<p class="textual">' + (esCorreo ? esc(s.vd) : esc(s.vd.replace(/^https?:\/\//, ""))) + '</p>' +
              '<p class="textual">Como está descrito en el catálogo: “' + esc(s.vo || "") + '”</p>'
            : '<div class="cta-falta">Todavía no hay una vía concreta registrada</div>' +
              '<p class="textual">El catálogo solo dice: “' + esc(s.vo || "sin información") + '”. Conviene consultar directamente con la unidad responsable.</p>') +
        '</div>' +
      '</div>' +
      '<aside class="col">' +
        '<div class="bloque">' +
          '<h2 class="rot">Quién puede solicitarlo</h2>' +
          '<div class="listilla">' + (solicitantes.length ? solicitantes.map(x => '<span class="mini">' + esc(x) + '</span>').join("") : '<span class="dato nulo">Sin definir</span>') + '</div>' +
        '</div>' +
        '<div class="bloque">' +
          '<h2 class="rot">Contacto</h2>' +
          '<p class="dato">' + contacto + '</p>' +
        '</div>' +
        '<div class="bloque">' +
          '<h2 class="rot">Lineamiento PDI</h2>' +
          '<div class="listilla">' + ((s.l || []).map(x => '<span class="mini">' + esc(x) + '</span>').join("") || '<span class="dato nulo">Sin asignar</span>') + '</div>' +
        '</div>' +
        '<div class="bloque">' +
          '<h2 class="rot">Procedencia del dato</h2>' +
          '<div class="proc">' +
            '<span>Información recogida de fuentes institucionales, pendiente de validación por la unidad responsable.</span>' +
            (s.fu ? '<span>Fuente: <a href="' + esc(s.fu) + '" target="_blank" rel="noopener">' + esc(s.fu.replace(/^https?:\/\//, "").slice(0, 40)) + '</a></span>' : '<span>Sin fuente registrada</span>') +
            '<span class="ref">' + esc(s.id) + '</span>' +
          '</div>' +
        '</div>' +
      '</aside>' +
    '</div>';
  document.title = s.n + " · Central de Iniciativas y Servicios";
  mostrar("vista-ficha");
}

/* ---------------- vista interna ---------------- */
function conteoPorDireccion() {
  const c = {};
  SERVICIOS.forEach(s => { c[s.d] = c[s.d] || { t: 0, v: 0 }; c[s.d].t++; if (s.vd) c[s.d].v++; });
  return c;
}

function pintarPanel(clave) {
  const p = $("panel"); p.innerHTML = "";

  const volverPortada = el("a", "volver");
  volverPortada.href = "#/";
  volverPortada.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg> Volver a la portada';
  p.appendChild(volverPortada);

  if (!clave) {
    const h = el("div", "encab");
    const t = el("div", "tick"); t.appendChild(el("h2", null, "Qué falta, dirección por dirección")); h.appendChild(t);
    h.appendChild(el("p", null, "Vista interna para las reuniones con cada dirección. Ordenadas de menor a mayor cobertura, así que arriba aparecen las conversaciones más urgentes."));
    p.appendChild(h);
    const cn = conteoPorDireccion(), lista = el("ul", "cobertura");
    Object.keys(cn).sort((a, b) => (cn[a].v / cn[a].t) - (cn[b].v / cn[b].t) || cn[b].t - cn[a].t).forEach(k => {
      const c = cn[k], pct = Math.round(100 * c.v / c.t);
      const b = el("button", "fila"); b.type = "button";
      b.appendChild(el("span", "nm", DIRS[k]));
      const barra = el("div", "barra");
      const ln = el("div", "linea-med"); ln.style.setProperty("--pct", pct + "%");
      barra.appendChild(ln); b.appendChild(barra);
      b.appendChild(el("span", pct < 50 ? "cifra bajo" : "cifra", c.v + "/" + c.t));
      b.addEventListener("click", () => irA("#/interno/" + k));
      const li = el("li"); li.appendChild(b); lista.appendChild(li);
    });
    p.appendChild(lista);
    document.title = "Vista interna · Central de Iniciativas y Servicios";
    return;
  }

  const servs = SERVICIOS.filter(s => s.d === clave);
  if (!servs.length) return irA("#/interno");
  const sinVia = servs.filter(s => !s.vd), conVia = servs.filter(s => s.vd), sinCorreo = servs.filter(s => !s.cc);

  const volver = el("button", "volver"); volver.type = "button";
  volver.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg> Todas las direcciones';
  volver.addEventListener("click", () => irA("#/interno"));
  p.appendChild(volver);

  const h = el("div", "encab");
  h.appendChild(el("h2", null, DIRS[clave]));
  h.appendChild(el("p", null, servs.length + " servicios levantados. " + conVia.length + " se pueden publicar en cuanto tengan sinónimos."));
  p.appendChild(h);

  const ped = el("div", "pedido");
  ped.appendChild(el("h3", null, "Lo que necesito de ustedes en la reunión"));
  const ol = el("ol");
  const l1 = el("li"); l1.innerHTML = "La vía concreta de <b>" + sinVia.length + "</b> servicio" + (sinVia.length === 1 ? "" : "s") + ": a qué correo, formulario o plataforma llega la solicitud.";
  const l2 = el("li"); l2.innerHTML = "Las palabras con que la gente les pide cada uno de los <b>" + servs.length + "</b>.";
  const l3 = el("li"); l3.innerHTML = "Confirmar los <b>" + servs.length + "</b> textos y decirme cuáles ya no existen. Un correo estable para <b>" + sinCorreo.length + "</b> que hoy no lo tienen.";
  ol.append(l1, l2, l3); ped.appendChild(ol); p.appendChild(ped);

  [{ t: "Falta la vía de solicitud", d: "Nadie puede llegar a estos hoy.", l: sinVia },
   { t: "Vía resuelta, falta validar", d: "Solo necesitan sinónimos y confirmación.", l: conVia }].forEach(g => {
    if (!g.l.length) return;
    const w = el("div", "grupo"), cab = el("div", "cab");
    cab.appendChild(el("h3", null, g.t));
    cab.appendChild(el("span", "n", g.l.length + " de " + servs.length));
    w.appendChild(cab); w.appendChild(el("p", "textual", g.d));
    const items = el("ul", "items");
    g.l.forEach(s => {
      const it = el("li", "item");
      it.appendChild(el("span", "t", s.n));
      it.appendChild(el("span", "d", s.cc || s.cn || "Sin contacto registrado"));
      const e = el("div", "e");
      e.appendChild(el("span", "mini no", "sinónimos"));
      if (!s.vd) e.appendChild(el("span", "mini no", "vía"));
      if (!s.cc) e.appendChild(el("span", "mini no", "correo"));
      it.appendChild(e); items.appendChild(it);
    });
    w.appendChild(items); p.appendChild(w);
  });
  document.title = DIRS[clave] + " · Vista interna";
}

/* ---------------- navegación ---------------- */
const VISTAS = ["vista-portada", "vista-estamento", "vista-ficha", "vista-interno"];

let primerRender = true;

function mostrar(id) {
  VISTAS.forEach(v => { $(v).hidden = (v !== id); });
  window.scrollTo({ top: 0, behavior: "instant" });
  // En una página de una sola vista, cambiar de sección no mueve el foco por
  // sí solo: quien usa lector de pantalla se queda oyendo la vista anterior.
  // Por eso se lleva el foco al encabezado de la vista recién mostrada.
  if (primerRender) { primerRender = false; return; }
  const enc = $(id).querySelector("h1, h2");
  if (enc) {
    if (!enc.hasAttribute("tabindex")) enc.setAttribute("tabindex", "-1");
    enc.focus({ preventScroll: true });
  }
}

function irA(hash) { window.location.hash = hash; }

function enrutar() {
  const h = (window.location.hash || "#/").replace(/^#/, "");
  const partes = h.split("/").filter(Boolean);

  if (partes[0] === "servicio" && partes[1]) return abrirFicha(decodeURIComponent(partes[1]));
  if (partes[0] === "estamento" && partes[1]) return abrirEstamento(partes[1]);
  if (partes[0] === "interno") { pintarPanel(partes[1] || null); return mostrar("vista-interno"); }

  estActual = null; rutaActiva = null;
  $("q-portada").value = "";
  renderPortada();
  document.title = "Central de Iniciativas y Servicios · Facultad de Medicina, Universidad de Chile";
  mostrar("vista-portada");
}

$("q-portada").addEventListener("input", renderPortada);
$("limpiar-portada").addEventListener("click", () => { $("q-portada").value = ""; renderPortada(); $("q-portada").focus(); });
$("q-est").addEventListener("input", renderEstamento);
$("limpiar-est").addEventListener("click", () => { $("q-est").value = ""; rutaActiva = null; pintarChips(); renderEstamento(); $("q-est").focus(); });
window.addEventListener("hashchange", enrutar);

pintarEstamentos();
enrutar();
