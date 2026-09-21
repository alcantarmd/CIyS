#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer(rel):
    p = RAIZ / rel
    if not p.exists():
        sys.exit(f"No encuentro {rel}. ¿Estás corriendo esto desde el repositorio?")
    return p.read_text(encoding="utf-8")


def imagen_datauri(rel):
    p = RAIZ / rel
    if not p.exists():
        sys.exit(f"No encuentro la imagen {rel}.")
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


def main():
    ap = argparse.ArgumentParser(description="Genera un HTML autocontenido del sitio.")
    ap.add_argument("--salida", default="dist/central-iniciativas-y-servicios.html")
    args = ap.parse_args()

    html = leer("index.html")
    css = leer("assets/css/estilos.css")
    js = leer("assets/js/app.js")
    datos = leer("data/servicios.js")

    # hoja de estilos -> <style> en línea
    html = re.sub(
        r'<link rel="stylesheet" href="assets/css/estilos\.css">',
        "<style>\n" + css + "\n</style>",
        html,
    )

    # escudos -> data URI
    for rel in ("assets/img/logo-universidad-de-chile.png",
                "assets/img/logo-facultad-de-medicina.png"):
        html = html.replace(f'src="{rel}"', f'src="{imagen_datauri(rel)}"')

    # scripts -> en línea, respetando el orden (datos primero)
    html = html.replace('<script src="data/servicios.js"></script>',
                        "<script>\n" + datos + "\n</script>")
    html = html.replace('<script src="assets/js/app.js"></script>',
                        "<script>\n" + js + "\n</script>")

    if "assets/" in html:
        sobra = sorted(set(re.findall(r'(?:src|href)="(assets/[^"]+)"', html)))
        if sobra:
            sys.exit("Quedaron referencias externas sin incrustar: " + ", ".join(sobra))

    salida = RAIZ / args.salida
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")

    kb = len(html.encode()) / 1024
    print(f"Listo: {salida.relative_to(RAIZ)}  ({kb:.0f} KB)")
    print("Se abre con doble clic, sin servidor y sin conexión.")


if __name__ == "__main__":
    main()
