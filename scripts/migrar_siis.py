#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrar_siis.py — Migración de "Central de Iniciativas y Servicios" al esquema del SIIS-FMUCH

Qué hace
--------
Toma la planilla actual (hojas "Servicios" e "Iniciativas") y produce la estructura
que necesita el sitio web cuando la web pasa a ser la fuente de verdad:

  1. Asigna identificadores estables e inmutables, y slugs para las URLs.
  2. Parte los campos multivalor en listas, respetando que el delimitador
     NO es el mismo en las dos hojas (";" en Servicios, "," en Iniciativas).
  3. Separa las celdas que hoy guardan dos datos: Contacto (nombre + correo)
     y Fuente (enlace + fecha de consulta).
  4. Rescata el correo o la URL que ya viene escrito dentro de "Cómo se solicita".
  5. Normaliza los años y marca explícitamente lo desconocido.
  6. Separa la columna "Tipo" de Iniciativas en tipo real y origen del dato.
  7. Aplica la regla de publicación y deja la lista de trabajo pendiente.

Qué NO hace (y no puede hacer)
------------------------------
No inventa sinónimos, no adivina vías de solicitud que no estén escritas, y no
clasifica misional/apoyo. Eso queda listado en la hoja "Pendientes".

Garantía: NUNCA modifica el archivo de entrada. Todo se escribe en la carpeta de salida.

Uso
---
    pip3 install openpyxl
    python3 migrar_siis.py "Central de Iniciativas y Servicios1.xlsx"
    python3 migrar_siis.py entrada.xlsx --salida ./migracion

Volver a correrlo sobre el mismo archivo conserva los identificadores ya asignados
(se guardan en ids_siis.json). Esa es la razón de ser del archivo: si un id cambia,
se rompe una URL que ya circuló.
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, OrderedDict
from datetime import datetime, date
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("Falta openpyxl.  Instálalo con:  pip3 install openpyxl")


# ==========================================================================
# CONFIGURACIÓN — esto es lo único que conviene editar
# ==========================================================================

# Delimitadores por hoja. Son distintos a propósito: así está la planilla hoy.
# En Servicios la coma aparece DENTRO de frases ("Departamentos, escuelas e
# institutos"), así que ahí solo se puede cortar por punto y coma.
SEP_SERVICIOS = ";"
SEP_INICIATIVAS = ","

# Vocabulario controlado de solicitantes.
# Cada regla es (expresión regular buscada en el texto normalizado, valor de destino).
# Se usan regex y no texto plano porque la planilla mezcla singular y plural
# ("Grupo de investigación" / "Grupos de investigación"): la "s?" evita
# duplicar cada regla. El orden importa: gana la primera que calce.
MAPA_SOLICITANTE = [
    (r"estudiantes? en situacion de discapacidad", "estudiante"),
    (r"estudiantes? de postgrado",                 "estudiante_postgrado"),
    (r"estudiantes? de pregrado",                  "estudiante_pregrado"),
    (r"estudiantes? extranjero",                   "externo"),
    (r"programas? de doctorado",                   "unidad_academica"),
    (r"programas? de postgrado",                   "unidad_academica"),
    (r"programas? de educacion continua",          "unidad_academica"),
    (r"centros? de estudiante",                    "estudiante"),
    (r"grupos? organizado",                        "estudiante"),
    (r"estudiante",                                "estudiante"),
    (r"nuevos? director",                          "autoridad_unidad"),
    (r"director",                                  "autoridad_unidad"),
    (r"academic",                                  "academico"),   # académicos y académicas
    (r"medicos? de campos clinicos",               "docente"),
    (r"coordinadores? de curso",                   "docente"),
    (r"asesor(?:es)? curricular",                  "docente"),
    (r"pec de curso",                              "docente"),
    (r"docente",                                   "docente"),
    (r"funcionari",                                "funcionario"),
    (r"personas? a honorario",                     "funcionario"),
    (r"equipos? de funcionario",                   "funcionario"),
    (r"gestor",                                    "funcionario"),
    (r"unidades? academica",                       "unidad_academica"),
    (r"unidad academica",                          "unidad_academica"),
    (r"unidades? receptora",                       "unidad_academica"),
    (r"escuela",                                   "unidad_academica"),
    (r"institut",                                  "unidad_academica"),
    (r"carrera",                                   "unidad_academica"),
    (r"departamento",                              "unidad_academica"),
    (r"direccion",                                 "direccion"),
    (r"grupos? de investigacion",                  "grupo_investigacion"),
    (r"proyectos? de investigacion",               "grupo_investigacion"),
    (r"proyecto",                                  "grupo_investigacion"),
    (r"establecimientos? escolar",                 "externo"),
    (r"postulantes? externo",                      "externo"),
    (r"comunidad (?:interna y )?externa",          "externo"),
    (r"profesional",                               "externo"),
    (r"egresado",                                  "externo"),
    (r"equipo",                                    "unidad_academica"),
]

# Direcciones canónicas. Cada entrada: clave -> (nombre para mostrar, patrones que la identifican).
# Se usa tanto para normalizar la columna "Dirección" de Servicios como para
# mapear los 104 textos libres de "Unidad Ejecutora" en Iniciativas.
DIRECCIONES = OrderedDict([
    ("academica",   ("Dirección Académica",                                  ["direccion academica", "dacademica"])),
    ("pregrado",    ("Dirección de Pregrado",                                ["pregrado"])),
    ("postgrado",   ("Dirección de Escuela de Postgrado",                    ["postgrado", "post grado"])),
    ("investigacion",("Dirección de Investigación e Innovación",             ["investigacion e innovacion", "direccion de investigacion"])),
    ("degi",        ("Dirección Económica y de Gestión Institucional (DEGI)",["degi", "economica y de gestion"])),
    ("dri",         ("Dirección de Relaciones Internacionales (DRI)",        ["relaciones internacionales", "dri", "rrii"])),
    ("digen",       ("Dirección de Igualdad de Género (DIGEN)",              ["igualdad de genero", "digen"])),
    ("daec",        ("Dirección de Asuntos Estudiantiles y Comunitarios (DAEC)", ["asuntos estudiantiles", "daec"])),
    ("clinica",     ("Dirección Clínica",                                    ["direccion clinica"])),
    ("extension",   ("Dirección de Extensión",                               ["direccion de extension", "extension y vinculacion"])),
    ("decanato",    ("Decanato",                                             ["decanato", "decano"])),
    ("nivel_central",("Universidad de Chile (nivel central)",                ["nivel central", "rectoria", "vti", "vid"])),
])

# Tipos reales de iniciativa. Todo lo que no calce aquí se considera ORIGEN del dato.
TIPOS_INICIATIVA = {"plan", "programa", "proyecto", "politica", "iniciativa"}

# Orígenes reconocidos en la columna "Tipo" (el defecto de las dos dimensiones).
MAPA_ORIGEN = [
    (r"hoja de ruta",   "hoja_de_ruta_decano"),
    (r"cuenta publica", "cuenta_publica"),
    (r"noticia",        "noticias"),
    (r"nivel central",  "nivel_central"),
    (r"rectoria",       "nivel_central"),
]

# Cómo se clasifica la vía de solicitud a partir del texto de "Cómo se solicita".
MAPA_VIA = [
    (r"formulario",       "formulario"),
    (r"postulaci",        "convocatoria"),
    (r"convocatoria",     "convocatoria"),
    (r"concurso",         "convocatoria"),
    (r"plataforma",       "plataforma"),
    (r"acceso web",       "plataforma"),
    (r"sistema en linea", "plataforma"),
    (r"correo",           "correo"),
    (r"e-?mail",          "correo"),
    (r"presencial",       "presencial"),
    (r"oficina",          "presencial"),
    (r"solicitud|solicita", "solicitud_informal"),
    (r"contacto",         "solicitud_informal"),
]

# Regla de publicación. Un servicio entra al buscador solo si cumple las tres.
REQUIERE_VIA_DESTINO = True
REQUIERE_SINONIMOS = True
REQUIERE_VIGENTE = True


# ==========================================================================
# UTILIDADES
# ==========================================================================

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# URL con esquema, o dominio suelto tipo "dacademica.med.uchile.cl/pdu" (frecuente en la planilla)
RE_URL_ESQUEMA = re.compile(r"https?://[^\s;,)\]]+")
RE_URL_SUELTA = re.compile(r"\b(?:[A-Za-z0-9\-]+\.)+(?:cl|com|org|net|edu)(?:/[^\s;,)\]]*)?\b")
RE_FECHA_PAREN = re.compile(r"\(([^)]*?(\d{2}[-/]\d{2}[-/]\d{4}|\d{4})[^)]*?)\)")


def norm(texto):
    """Minúsculas, sin tildes, sin espacios repetidos. Para comparar, nunca para mostrar."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def slugify(texto, largo=70):
    s = norm(texto)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > largo:
        s = s[:largo].rsplit("-", 1)[0]
    return s or "sin-nombre"


def limpiar(v):
    """Valor de celda -> str limpio, o None si está realmente vacío."""
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("none", "n/a", "-") else None


def partir(valor, sep):
    """Parte un campo multivalor por el delimitador de SU hoja."""
    if not valor:
        return []
    return [p.strip() for p in str(valor).split(sep) if p.strip()]


def extraer_contactos(*textos):
    """Devuelve (correos, urls) encontrados en los textos dados, sin duplicados y en orden."""
    correos, urls = [], []
    for t in textos:
        if not t:
            continue
        s = str(t)
        for m in RE_EMAIL.findall(s):
            if m not in correos:
                correos.append(m)
        # se quitan los correos antes de buscar dominios, para no confundir el dominio del correo
        sin_correos = RE_EMAIL.sub(" ", s)
        for m in RE_URL_ESQUEMA.findall(sin_correos):
            u = m.rstrip(".,;")
            if u not in urls:
                urls.append(u)
        sin_urls = RE_URL_ESQUEMA.sub(" ", sin_correos)
        for m in RE_URL_SUELTA.findall(sin_urls):
            u = "https://" + m.rstrip(".,;")
            if u not in urls:
                urls.append(u)
    return correos, urls


def separar_contacto(texto):
    """'Dra. Olga Toro / dpi.med@uchile.cl' -> ('Dra. Olga Toro', 'dpi.med@uchile.cl')"""
    if not texto:
        return None, None
    correos = RE_EMAIL.findall(str(texto))
    correo = correos[0] if correos else None
    nombre = RE_EMAIL.sub("", str(texto))
    nombre = nombre.replace("/", " ").strip(" ;,-")
    nombre = re.sub(r"\s+", " ", nombre)
    return (nombre or None), correo


def mapear_lista(atomos, mapa):
    """Aplica un mapa de patrones a cada átomo. Devuelve (valores, no_mapeados)."""
    salida, sin_mapear = [], []
    for a in atomos:
        na = norm(a)
        destino = None
        for patron, valor in mapa:
            if re.search(patron, na):
                destino = valor
                break
        if destino:
            if destino not in salida:
                salida.append(destino)
        else:
            sin_mapear.append(a)
    return salida, sin_mapear


def mapear_direccion(texto):
    """Texto libre -> clave de dirección canónica, o None."""
    n = norm(texto)
    for clave, (_, patrones) in DIRECCIONES.items():
        for p in patrones:
            if re.search(p, n):
                return clave
    return None


def clasificar_via(texto):
    n = norm(texto)
    for patron, valor in MAPA_VIA:
        if re.search(patron, n):
            return valor
    return "indeterminada"


def parsear_anio(v):
    """
    Devuelve (anio:int|None, nota:str|None).
    La planilla mezcla año suelto como número (2015.0) con fecha completa (2026-07-20).
    """
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, None
    if isinstance(v, (datetime, date)):
        return v.year, "venía como fecha completa"
    try:
        f = float(str(v).strip())
        a = int(f)
        if 1900 <= a <= 2100:
            return a, None
        return None, f"valor fuera de rango: {v}"
    except (TypeError, ValueError):
        m = re.search(r"(19|20)\d{2}", str(v))
        if m:
            return int(m.group(0)), f"año extraído del texto: {v}"
        return None, f"no interpretable: {v}"


def parsear_fuentes(texto):
    """
    'url (19-03-2026); url2 (Cuenta Pública)' -> [{url, etiqueta, consultada_el}, ...]
    Separa el enlace de la fecha o nota que hoy viven en la misma celda.
    """
    if not texto:
        return []
    fuentes = []
    for trozo in str(texto).split(";"):
        trozo = trozo.strip()
        if not trozo:
            continue
        etiqueta = None
        m = RE_FECHA_PAREN.search(trozo)
        if m:
            etiqueta = m.group(1).strip()
        else:
            mp = re.search(r"\(([^)]+)\)", trozo)
            if mp:
                etiqueta = mp.group(1).strip()
        _, urls = extraer_contactos(trozo)
        sin_url = RE_URL_ESQUEMA.sub("", trozo)
        sin_url = re.sub(r"\([^)]*\)", "", sin_url).strip(" .,;")
        fuentes.append({
            "url": urls[0] if urls else None,
            "etiqueta": etiqueta or (sin_url or None),
            "texto_original": trozo,
        })
    return fuentes


class Registro:
    """
    Libro de identificadores. Guarda nombre normalizado -> id.
    Existe para que volver a correr el script no reasigne ids: un id que cambia
    es una URL que se rompe.
    """

    def __init__(self, ruta):
        self.ruta = Path(ruta)
        self.datos = {"servicios": {}, "iniciativas": {}, "slugs": {}}
        if self.ruta.exists():
            try:
                self.datos.update(json.loads(self.ruta.read_text(encoding="utf-8")))
            except Exception as e:
                print(f"  ! No se pudo leer {self.ruta.name} ({e}); se asignan ids nuevos.")

    def id_para(self, coleccion, clave, prefijo):
        tabla = self.datos.setdefault(coleccion, {})
        if clave in tabla:
            return tabla[clave], False
        usados = {int(v.split("-")[-1]) for v in tabla.values() if v.split("-")[-1].isdigit()}
        siguiente = max(usados) + 1 if usados else 1
        nuevo = f"{prefijo}-{siguiente:03d}"
        tabla[clave] = nuevo
        return nuevo, True

    def slug_unico(self, base, id_propio):
        tabla = self.datos.setdefault("slugs", {})
        for slug, duenio in tabla.items():
            if duenio == id_propio:
                return slug          # ya tenía slug: se conserva aunque el nombre cambie
        candidato, n = base, 2
        while candidato in tabla:
            candidato = f"{base}-{n}"
            n += 1
        tabla[candidato] = id_propio
        return candidato

    def guardar(self):
        self.ruta.write_text(json.dumps(self.datos, ensure_ascii=False, indent=2), encoding="utf-8")


# ==========================================================================
# LECTURA
# ==========================================================================

def leer_hoja(wb, nombre):
    if nombre not in wb.sheetnames:
        sys.exit(f"La planilla no tiene una hoja llamada '{nombre}'. Hojas encontradas: {wb.sheetnames}")
    ws = wb[nombre]
    encabezados = [c.value for c in ws[1]]
    filas = []
    for i, fila in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(v is None or str(v).strip() == "" for v in fila):
            continue
        d = dict(zip(encabezados, fila))
        d["_fila_excel"] = i
        filas.append(d)
    return filas


def col(fila, *nombres):
    """Busca una columna por varios nombres posibles (la planilla tiene 'TIpo' con typo)."""
    for n in nombres:
        if n in fila:
            return fila[n]
    for n in nombres:
        for k in fila:
            if k and norm(k) == norm(n):
                return fila[k]
    return None


# ==========================================================================
# TRANSFORMACIÓN — SERVICIOS
# ==========================================================================

def migrar_servicios(filas, reg, informe):
    salida, pendientes = [], []

    for f in filas:
        nombre = limpiar(col(f, "Servicio"))
        if not nombre:
            continue
        clave = norm(nombre)
        sid, es_nuevo = reg.id_para("servicios", clave, "svc")
        if es_nuevo:
            informe["servicios_nuevos"] += 1
        slug = reg.slug_unico(slugify(nombre), sid)

        direccion_txt = limpiar(col(f, "Dirección"))
        direccion_id = mapear_direccion(direccion_txt)
        dnom = DIRECCIONES[direccion_id][0] if direccion_id else (direccion_txt or "(sin dirección)")
        if not direccion_id:
            pendientes.append((dnom, sid, nombre, "Dirección no reconocida", direccion_txt or ""))

        como = limpiar(col(f, "Cómo se solicita"))
        contacto = limpiar(col(f, "Contacto"))
        contacto_nombre, contacto_correo = separar_contacto(contacto)

        # El rescate: el correo o la URL muchas veces ya está escrito dentro de
        # "Cómo se solicita", solo que enterrado en la frase.
        # Se miran las dos columnas por separado para poder decir con honestidad
        # cuántas vías se recuperaron de verdad y cuántas ya estaban en Contacto.
        correos_c, urls_c = extraer_contactos(contacto)
        correos_k, urls_k = extraer_contactos(como)

        # Preferencia: formulario o plataforma antes que un correo personal,
        # y el correo de la unidad antes que el de una persona.
        via_destino = urls_k[0] if urls_k else (
            correos_c[0] if correos_c else (
                correos_k[0] if correos_k else (
                    urls_c[0] if urls_c else None)))

        tenia_en_contacto = bool(correos_c or urls_c)
        via_destino_origen = None
        if via_destino:
            if tenia_en_contacto and via_destino in (correos_c + urls_c):
                via_destino_origen = "Contacto"
            else:
                via_destino_origen = "rescatado de 'Cómo se solicita'"
                if not tenia_en_contacto:
                    # Solo cuenta como rescate real si la columna Contacto no
                    # servía: son las filas que sin el script quedaban sin vía.
                    informe["vias_rescatadas"] += 1
                else:
                    informe["vias_mejoradas"] += 1

        # El texto puede decir "Solicitud a la Subdirección" y traer igual una URL
        # al final: manda el destino real, no la frase.
        via_tipo = clasificar_via(como)
        if via_destino:
            if via_destino.startswith("http") and via_tipo in ("solicitud_informal", "indeterminada"):
                via_tipo = "plataforma"
            elif "@" in via_destino and via_tipo in ("solicitud_informal", "indeterminada"):
                via_tipo = "correo"

        solicitantes_raw = partir(col(f, "Quién puede solicitarlo"), SEP_SERVICIOS)
        solicitantes, sin_mapear = mapear_lista(solicitantes_raw, MAPA_SOLICITANTE)
        for s in sin_mapear:
            informe["solicitantes_sin_mapear"][s] += 1

        lineamientos = partir(col(f, "Lineamiento PDI"), SEP_SERVICIOS)

        fuente = limpiar(col(f, "Fuente"))
        _, fuente_urls = extraer_contactos(fuente)

        registro = OrderedDict([
            ("id", sid),
            ("slug", slug),
            ("nombre", nombre),
            ("sinonimos", []),                                   # PENDIENTE: a mano
            ("direccion_id", direccion_id),
            ("direccion_nombre", dnom),
            ("unidad", limpiar(col(f, "Unidad / Subdirección"))),
            ("que_entrega", limpiar(col(f, "Qué entrega concretamente"))),
            ("quien_solicita", solicitantes),
            ("quien_solicita_original", limpiar(col(f, "Quién puede solicitarlo"))),
            ("via_tipo", via_tipo),
            ("via_destino", via_destino),
            ("via_destino_origen", via_destino_origen),
            ("via_texto_original", como),
            ("contacto_nombre", contacto_nombre),
            ("contacto_correo", contacto_correo),
            ("lineamiento", lineamientos),
            ("proceso", None),                                   # PENDIENTE: misional | apoyo
            ("periodicidad", None),                              # PENDIENTE
            ("vigencia", "vigente"),                             # supuesto inicial, revisable
            ("fuente_url", fuente_urls[0] if fuente_urls else None),
            ("fuente_consultada_el", None),
            ("confianza", limpiar(col(f, "Confianza"))),
            ("validado_por", limpiar(col(f, "Validado por"))),
            ("validado_el", None),
            ("_fila_excel", f["_fila_excel"]),
        ])

        # Regla de publicación
        faltas = []
        if REQUIERE_VIA_DESTINO and not via_destino:
            faltas.append("sin vía de destino")
        if REQUIERE_SINONIMOS and not registro["sinonimos"]:
            faltas.append("sin sinónimos")
        if REQUIERE_VIGENTE and registro["vigencia"] != "vigente":
            faltas.append("no vigente")
        registro["publicable"] = not faltas
        registro["falta_para_publicar"] = "; ".join(faltas) or None
        # Lo único que separa a este servicio de ser publicable son los sinónimos,
        # que es trabajo de escritorio y no depende de nadie más.
        registro["falta_solo_sinonimos"] = faltas == ["sin sinónimos"]

        if not via_destino:
            pendientes.append((dnom, sid, nombre, "1. Falta vía de solicitud accionable",
                               f"dice: {como or '(vacío)'}"))
        pendientes.append((dnom, sid, nombre, "2. Faltan sinónimos",
                           "¿con qué palabras lo pide la gente?"))
        pendientes.append((dnom, sid, nombre, "3. Falta clasificar proceso", "misional o apoyo"))
        if not registro["validado_por"]:
            pendientes.append((dnom, sid, nombre, "4. Sin validar por la dirección", ""))

        salida.append(registro)

    return salida, pendientes


# ==========================================================================
# TRANSFORMACIÓN — INICIATIVAS
# ==========================================================================

def migrar_iniciativas(filas, reg, informe):
    salida, pendientes = [], []

    for f in filas:
        nombre = limpiar(col(f, "Nombre"))
        if not nombre:
            continue

        # El N° ya es un buen identificador: 1..132 sin saltos ni repetidos.
        numero = col(f, "N°", "N", "Nº")
        try:
            n = int(float(str(numero).strip()))
            iid = f"ini-{n:03d}"
        except (TypeError, ValueError):
            iid, _ = reg.id_para("iniciativas", norm(nombre), "ini")
        reg.datos.setdefault("iniciativas", {})[norm(nombre)] = iid
        slug = reg.slug_unico(slugify(nombre), iid)

        # Defecto 06: una columna con dos dimensiones.
        tipo_txt = limpiar(col(f, "TIpo", "Tipo")) or ""
        ntipo = norm(tipo_txt)
        tipo, origen = None, None
        for clave in TIPOS_INICIATIVA:
            if clave in ntipo:
                tipo = clave
                break
        for patron, valor in MAPA_ORIGEN:
            if patron in ntipo:
                origen = valor
                break
        if origen and not tipo:
            # Es el caso de "Hoja de Ruta Decano": sabemos de dónde salió, no qué es.
            tipo = None
            informe["tipos_por_reclasificar"] += 1
            pendientes.append(("(iniciativas)", iid, nombre, "5. Falta tipo real",
                               f"'{tipo_txt}' indica origen, no tipo"))

        a_ini, nota_ini = parsear_anio(col(f, "Fecha Inicio"))
        a_fin, nota_fin = parsear_anio(col(f, "Fecha Termino", "Fecha Término"))
        if nota_ini or nota_fin:
            informe["fechas_ajustadas"] += 1

        ejec_txt = limpiar(col(f, "Unidad Ejecutora")) or ""
        # El separador real de co-ejecutores aquí es la barra, no la coma.
        atomos = [p.strip() for p in re.split(r"[/;]", ejec_txt) if p.strip()]
        ejecutores, ejec_sin_mapear = [], []
        for a in atomos:
            clave = mapear_direccion(a)
            if clave:
                if clave not in ejecutores:
                    ejecutores.append(clave)
            else:
                ejec_sin_mapear.append(a)
        if not ejecutores:
            pendientes.append(("(iniciativas)", iid, nombre,
                               "6. Ejecutor sin mapear a dirección", ejec_txt[:90]))
            informe["ejecutores_sin_mapear"] += 1

        registro = OrderedDict([
            ("id", iid),
            ("slug", slug),
            ("nombre", nombre),
            ("descripcion", limpiar(col(f, "Descripción Breve"))),
            ("tipo", tipo),
            ("origen", origen),
            ("tipo_original", tipo_txt or None),
            ("estado", limpiar(col(f, "Estado"))),
            ("anio_inicio", a_ini),
            ("anio_termino", a_fin),
            ("sin_termino_definido", a_fin is None),
            ("nota_fechas", "; ".join(x for x in (nota_ini, nota_fin) if x) or None),
            ("ejecutores", ejecutores),
            ("ejecutores_sin_mapear", ejec_sin_mapear),
            ("ejecutor_original", ejec_txt or None),
            ("encargado", limpiar(col(f, "Encargado"))),
            ("lineamiento", partir(col(f, "Lineamiento"), SEP_INICIATIVAS)),
            ("area_tematica", limpiar(col(f, "Area Temática / Eje Institucional",
                                           "Área Temática / Eje Institucional"))),
            ("periodo_original", limpiar(col(f, "Periodo"))),
            ("fuentes", parsear_fuentes(limpiar(col(f, "Fuente / Observaciones")))),
            ("servicios_relacionados", []),                      # PENDIENTE: el puente que hoy falta
            ("_fila_excel", f["_fila_excel"]),
        ])
        salida.append(registro)

    return salida, pendientes


# ==========================================================================
# ESCRITURA
# ==========================================================================

AZUL = "1F3B4D"
GRIS = "E9EEF1"


def _encabezar(ws, columnas):
    ws.append(columnas)
    for i, _ in enumerate(columnas, start=1):
        c = ws.cell(row=1, column=i)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def _autoancho(ws, maximo=60):
    for col_cells in ws.columns:
        largo = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = min(max(largo + 2, 10), maximo)


def _valor(v):
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return " | ".join(x.get("url") or x.get("etiqueta") or "" for x in v)
        return "; ".join(str(x) for x in v)
    if isinstance(v, bool):
        return "sí" if v else "no"
    return v


def escribir_excel(ruta, servicios, iniciativas, pendientes, informe):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    campos_srv = [k for k in servicios[0].keys() if not k.startswith("_")] if servicios else []
    ws = wb.create_sheet("Servicios")
    _encabezar(ws, campos_srv)
    for r in servicios:
        ws.append([_valor(r.get(k)) for k in campos_srv])
    # Gris = servicio sin vía accionable. Es el bloqueo que depende de otros;
    # los sinónimos, en cambio, los puedes escribir tú.
    ivia = campos_srv.index("via_destino") + 1 if "via_destino" in campos_srv else None
    if ivia:
        for fila in range(2, ws.max_row + 1):
            if not ws.cell(row=fila, column=ivia).value:
                for c in range(1, len(campos_srv) + 1):
                    ws.cell(row=fila, column=c).fill = PatternFill("solid", fgColor=GRIS)
    _autoancho(ws)

    campos_ini = [k for k in iniciativas[0].keys() if not k.startswith("_")] if iniciativas else []
    ws = wb.create_sheet("Iniciativas")
    _encabezar(ws, campos_ini)
    for r in iniciativas:
        ws.append([_valor(r.get(k)) for k in campos_ini])
    _autoancho(ws)

    # Ordenada por dirección a propósito: así se filtra y se le manda a cada
    # dirección exactamente su lista, en un solo correo.
    ws = wb.create_sheet("Pendientes")
    _encabezar(ws, ["dirección", "id", "nombre", "qué falta", "detalle"])
    for p in sorted(pendientes, key=lambda x: (x[0], x[3], x[1])):
        ws.append(list(p))
    ws.auto_filter.ref = f"A1:E{ws.max_row}"
    _autoancho(ws)

    ws = wb.create_sheet("Vocabularios")
    _encabezar(ws, ["vocabulario", "clave", "valor visible"])
    for clave, (nombre, _) in DIRECCIONES.items():
        ws.append(["direccion", clave, nombre])
    for v in sorted({v for _, v in MAPA_SOLICITANTE}):
        ws.append(["quien_solicita", v, v.replace("_", " ")])
    for v in sorted({v for _, v in MAPA_VIA} | {"indeterminada"}):
        ws.append(["via_tipo", v, v.replace("_", " ")])
    for v in sorted(TIPOS_INICIATIVA):
        ws.append(["tipo_iniciativa", v, v])
    for v in sorted({v for _, v in MAPA_ORIGEN}):
        ws.append(["origen_iniciativa", v, v.replace("_", " ")])
    for v in ["vigente", "suspendido", "discontinuado"]:
        ws.append(["vigencia", v, v])
    for v in ["misional", "apoyo"]:
        ws.append(["proceso", v, v])
    _autoancho(ws)

    ws = wb.create_sheet("Informe")
    _encabezar(ws, ["indicador", "valor"])
    for k, v in informe["resumen"]:
        ws.append([k, v])
    _autoancho(ws)

    wb.save(ruta)


# ==========================================================================
# PRINCIPAL
# ==========================================================================

def main():
    ap = argparse.ArgumentParser(description="Migra la planilla FMUCH al esquema del SIIS.")
    ap.add_argument("entrada", help="Ruta del .xlsx original (no se modifica)")
    ap.add_argument("--salida", default="migracion_siis", help="Carpeta de salida")
    ap.add_argument("--hoja-servicios", default="Servicios")
    ap.add_argument("--hoja-iniciativas", default="Iniciativas")
    args = ap.parse_args()

    entrada = Path(args.entrada).expanduser()
    if not entrada.exists():
        sys.exit(f"No encuentro el archivo: {entrada}")
    salida = Path(args.salida).expanduser()
    salida.mkdir(parents=True, exist_ok=True)

    print(f"\nLeyendo  {entrada.name}")
    wb = openpyxl.load_workbook(entrada, data_only=True)
    filas_srv = leer_hoja(wb, args.hoja_servicios)
    filas_ini = leer_hoja(wb, args.hoja_iniciativas)
    print(f"         {len(filas_srv)} servicios, {len(filas_ini)} iniciativas")

    reg = Registro(salida / "ids_siis.json")
    informe = {
        "servicios_nuevos": 0,
        "vias_rescatadas": 0,
        "vias_mejoradas": 0,
        "fechas_ajustadas": 0,
        "tipos_por_reclasificar": 0,
        "ejecutores_sin_mapear": 0,
        "solicitantes_sin_mapear": Counter(),
    }

    servicios, pend_srv = migrar_servicios(filas_srv, reg, informe)
    iniciativas, pend_ini = migrar_iniciativas(filas_ini, reg, informe)
    pendientes = pend_srv + pend_ini
    reg.guardar()

    publicables = sum(1 for s in servicios if s["publicable"])
    a_un_paso = sum(1 for s in servicios if s["falta_solo_sinonimos"])
    con_via = sum(1 for s in servicios if s["via_destino"])
    con_correo = sum(1 for s in servicios if s["contacto_correo"])
    sin_validar = sum(1 for s in servicios if not s["validado_por"])
    por_direccion = Counter(s["direccion_nombre"] for s in servicios)
    via_por_dir = Counter(s["direccion_nombre"] for s in servicios if s["via_destino"])

    informe["resumen"] = [
        ("Servicios procesados", len(servicios)),
        ("Iniciativas procesadas", len(iniciativas)),
        ("", ""),
        ("Servicios con vía de destino accionable", con_via),
        ("  ...que sin el script quedaban sin vía", informe["vias_rescatadas"]),
        ("  ...que además ganaron un destino mejor", informe["vias_mejoradas"]),
        ("Servicios SIN vía accionable (hay que pedirla)", len(servicios) - con_via),
        ("Servicios con correo de contacto", con_correo),
        ("Servicios sin validar por su dirección", sin_validar),
        ("", ""),
        ("Publicables HOY", f"{publicables} de {len(servicios)}"),
        ("Publicables al cargar solo los sinónimos", f"{a_un_paso} de {len(servicios)}"),
        ("", ""),
        ("Iniciativas cuyo 'Tipo' era en realidad origen", informe["tipos_por_reclasificar"]),
        ("Iniciativas con fechas ajustadas o inferidas", informe["fechas_ajustadas"]),
        ("Iniciativas sin ejecutor mapeable a una dirección", informe["ejecutores_sin_mapear"]),
        ("Solicitantes que no calzaron en el vocabulario", len(informe["solicitantes_sin_mapear"])),
        ("Tareas pendientes registradas", len(pendientes)),
    ]

    escribir_excel(salida / "SIIS - datos migrados.xlsx", servicios, iniciativas, pendientes, informe)

    def limpio(lista):
        return [{k: v for k, v in r.items() if not k.startswith("_")} for r in lista]

    (salida / "servicios.json").write_text(
        json.dumps(limpio(servicios), ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "iniciativas.json").write_text(
        json.dumps(limpio(iniciativas), ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "vocabularios.json").write_text(json.dumps({
        "direcciones": {k: v[0] for k, v in DIRECCIONES.items()},
        "quien_solicita": sorted({v for _, v in MAPA_SOLICITANTE}),
        "via_tipo": sorted({v for _, v in MAPA_VIA} | {"indeterminada"}),
        "tipo_iniciativa": sorted(TIPOS_INICIATIVA),
        "origen_iniciativa": sorted({v for _, v in MAPA_ORIGEN}),
        "vigencia": ["vigente", "suspendido", "discontinuado"],
        "proceso": ["misional", "apoyo"],
        "lineamiento": ["Docencia", "Investigación", "Extensión y VM", "Gestión Interna", "Bienestar"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # -------------------- informe en pantalla --------------------
    print("\n" + "=" * 66)
    print("RESULTADO")
    print("=" * 66)
    for k, v in informe["resumen"]:
        print("" if not k else f"  {k:.<52} {v}")

    print("\n  Cobertura por dirección (con vía accionable / total)")
    print("  " + "-" * 62)
    for d, total in por_direccion.most_common():
        c = via_por_dir.get(d, 0)
        barra = "█" * round(12 * c / total) + "·" * (12 - round(12 * c / total))
        print(f"  {d[:44]:.<46} {barra} {c:3d}/{total}")

    if informe["solicitantes_sin_mapear"]:
        print("\n  Solicitantes sin vocabulario (revisa MAPA_SOLICITANTE arriba):")
        for k, v in informe["solicitantes_sin_mapear"].most_common(15):
            print(f"    {v:3d}x  {k}")

    sin_ejec = [i for i in iniciativas if not i["ejecutores"]]
    if sin_ejec:
        print(f"\n  {len(sin_ejec)} iniciativas sin dirección ejecutora. No es un error del")
        print("  script: casi todas las ejecutan escuelas, institutos o la Facultad")
        print("  entera, que no son ninguna de las 12 direcciones. Hacen falta esos")
        print("  niveles en el vocabulario, o dejarlas sin dirección a propósito.")
        for i in sin_ejec[:5]:
            print(f"    {i['id']}  {(i['ejecutor_original'] or '')[:62]}")

    print(f"\n  Escrito en  {salida.resolve()}")
    for f in sorted(salida.iterdir()):
        print(f"    - {f.name}")
    print("\n  El archivo de entrada no fue modificado.")
    print("  ids_siis.json guarda los identificadores: no lo borres ni lo edites a mano.\n")


if __name__ == "__main__":
    main()
