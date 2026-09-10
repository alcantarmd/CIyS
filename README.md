# Central de Iniciativas y Servicios

Catálogo de servicios de la Facultad de Medicina de la Universidad de Chile, organizado desde la pregunta de quien consulta y no desde el organigrama.

Unidad responsable: **Dirección Académica, Unidad de Plan de Desarrollo y Autoevaluación Institucional**.

> **Estado: MVP.** Esta versión cubre solo los **servicios**. Las iniciativas, que dan la otra mitad del nombre, entran en una fase posterior. El catálogo aún no ha sido validado por las unidades responsables, y por eso el sitio se publica con `noindex`.

## Qué hace

- **Buscador** sobre el catálogo completo, tolerante a tildes y a orden de palabras.
- **Tres entradas por estamento**: académicos, estudiantes y funcionarios. Cada una muestra solo lo que puede solicitar ese estamento.
- **Rutas por pregunta**: atajos redactados desde el problema de la persona ("me toca hacer el PDU de mi unidad") y no desde el nombre oficial del servicio.
- **Ficha por servicio con URL propia**, para poder enlazarla desde un correo o desde el sitio de una dirección.
- **Vista interna** de cobertura por dirección, que es la herramienta de trabajo para las reuniones de validación.

## Cómo se ve en tu computador

No hay build ni dependencias. Basta abrir `index.html` en el navegador.

Para que se comporte igual que en producción, conviene servirlo:

```bash
npx serve .
# o
python3 -m http.server 8000
```

## Estructura

```
index.html                  una sola página, todo el enrutado ocurre en el hash
assets/css/estilos.css      sistema de diseño completo, con la marca institucional
assets/js/app.js            búsqueda, filtros por estamento, fichas y enrutado
assets/img/                 escudos de Universidad y Facultad
data/servicios.js           el catálogo (window.SERVICIOS)
scripts/migrar_siis.py      genera los datos desde la planilla maestra
scripts/construir_pagina_unica.py   arma un HTML autocontenido para compartir
vercel.json                 configuración de despliegue y cabeceras
```

## De dónde salen los datos

`data/servicios.js` **no se edita a mano.** Se genera desde la planilla maestra:

```bash
pip3 install openpyxl
python3 scripts/migrar_siis.py "Central de Iniciativas y Servicios.xlsx" --salida migracion
```

Eso produce un `servicios.json`. Para convertirlo en el archivo que carga el sitio:

```bash
python3 - <<'PY'
import json, pathlib
d = json.load(open('migracion/servicios.json'))
campos = ('id','sl','n','d','u','q','s','vt','vd','vo','cn','cc','l','cf','fu')
corto = [{k: r[k] for k in campos if k in r} for r in d]
pathlib.Path('data/servicios.js').write_text(
    'window.SERVICIOS=' + json.dumps(corto, ensure_ascii=False, separators=(',',':')) + ';',
    encoding='utf-8')
PY
```

El script de migración guarda además `ids_siis.json`, que conserva los identificadores y los slugs entre corridas. **No lo borres ni lo edites**: un id que cambia es una URL de ficha que se rompe.

## Enrutado

Las rutas viven en el hash, así que no hacen falta reescrituras en el servidor y cualquier hosting estático sirve.

| Ruta | Muestra |
|---|---|
| `#/` | Portada con buscador y los tres estamentos |
| `#/estamento/academico` | Servicios para académicos (`estudiante`, `funcionario`) |
| `#/servicio/<slug>` | Ficha de un servicio |
| `#/interno` | Cobertura por dirección |
| `#/interno/<direccion>` | Lo que falta en una dirección |

## Marca

Color y tipografía provienen de *Gráfica institucional 2026* de la Escuela de Salud Pública. El naranja `#FF9D18` es el acento; el azul `#092F9D`, la estructura. La tipografía es Calibri, con **Carlito** como sustituto métrico de código abierto para equipos que no la tengan.

El sitio es de **tema claro único**, a propósito: el manual es claro y los escudos son oscuros sobre fondo claro. Invertirlos para un modo oscuro rompería la marca.

Todos los pares de texto y fondo se verificaron contra WCAG AA (4.5:1).

## Pendiente

- Sinónimos por servicio. Es el campo que decide si el buscador sirve, y hoy está vacío en los 111.
- Vía de solicitud concreta para los servicios que no la tienen.
- Validación por cada dirección responsable.
- Clasificación de cada servicio en proceso misional o de apoyo.
- Las iniciativas, que completan el alcance del nombre.
