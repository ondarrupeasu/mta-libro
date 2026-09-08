#!/usr/bin/env python3
"""Genera Paquetes de contenidos IMS (importables en Moodle 4.5) desde los unit*.html.

Reutiliza el patrón de libro-sostenibilidad/moodle/sortu_moodle.py:
- toma el <main> de cada docs/unitN.html (contenido del libro, con Update 2026 / Legacy / deck),
- EMBEBE las imágenes como data: URI  ->  .zip autónomo (sin ficheros sueltos),
- quita el "chrome" del sitio (barras laterales, buscador, botones de edición, scripts),
- envuelve en una página HTML propia con CSS neutro (se pierde la casa coral, look Moodle).

Uso:  python3 moodle/sortu_moodle.py 1      (una unidad, spike)
      python3 moodle/sortu_moodle.py all    (las 7 units)
      python3 moodle/sortu_moodle.py guide  (planificador -> recurso OCULTO de profesor)
Salida: moodle/dist/IMSCP-unitN.zip   (subir a Moodle como "Paquete de contenidos IMS", OCULTO)
"""
import sys, re, base64, zipfile, html as H
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT  = Path(__file__).resolve().parent / "dist"; OUT.mkdir(parents=True, exist_ok=True)

CSS = (
 "body{font-family:system-ui,Segoe UI,Roboto,sans-serif;line-height:1.6;max-width:860px;"
 "margin:0 auto;padding:1rem 1.2rem;color:#1c2024;background:#fff}"
 "h1{font-size:1.7rem;line-height:1.15;border-bottom:3px solid #b23b2e;padding-bottom:.35rem}"
 "h2{font-size:1.3rem;margin-top:2rem}h3{font-size:1.08rem;margin-top:1.4rem;color:#33383e}"
 "p{margin:0 0 .8rem}a{color:#b23b2e}"
 "figure{margin:1.2rem 0;text-align:center}img{max-width:100%;height:auto;border:1px solid #e2ddd4;border-radius:6px}"
 "figcaption{font-size:.8rem;color:#6b6660;margin-top:.3rem}"
 ".callout{border-left:4px solid #c9c4ba;background:#faf9f7;border-radius:0 8px 8px 0;padding:.6rem .9rem;margin:1rem 0}"
 ".callout-h{font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;margin-bottom:.2rem}"
 ".callout.remember{border-color:#2563eb;background:#f2f6ff}.callout.advice{border-color:#7c3aed;background:#f7f3ff}"
 ".callout.activity{border-color:#059669;background:#eefcf5}.callout.practice{border-color:#d97706;background:#fff7ed}"
 ".callout.video{border-color:#dc2626;background:#fef4f4}"
 ".block{border-radius:10px;padding:.8rem 1.1rem;margin:1.2rem 0}"
 ".block-tag{display:inline-block;font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;"
 "padding:.15rem .6rem;border-radius:20px;margin-bottom:.4rem;color:#fff}"
 ".block.update{background:#ecfdf9;border:1px solid #bfe9e2;box-shadow:inset 4px 0 0 #0f766e}"
 ".block.update .block-tag{background:#0f766e}.block.update h3{color:#0f766e}"
 ".block.legacy{background:#f7f2e7;border:1px dashed #d8c9a6}.block.legacy .block-tag{background:#8a6d3b}"
 ".block.legacy p{color:#5f533a}.block p.sources{font-size:.8rem;opacity:.85}"
 ".deck{margin:2rem 0;padding:1rem 1.2rem;border:1px solid #cdd6ee;border-radius:12px;background:#f6f8ff}"
 ".deck-tag{display:inline-block;font-size:.7rem;font-weight:700;text-transform:uppercase;padding:.15rem .6rem;"
 "border-radius:20px;margin-bottom:.4rem;background:#4f46e5;color:#fff}"
 ".deck h2,.deck h3{color:#3730a3;border:0}.deck-credit{font-size:.85rem;color:#6b7280}"
 "table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ccc;padding:.4rem .6rem;text-align:left;vertical-align:top}"
)

def embed_images(main_html, base=DOCS):
    """Reemplaza src="img/..." por data: URI leyendo de docs/."""
    def repl(m):
        rel = m.group(1)
        p = base / rel
        if not p.exists():
            return m.group(0)
        ext = p.suffix.lower().lstrip(".")
        mime = "image/png" if ext == "png" else ("image/svg+xml" if ext == "svg" else "image/jpeg")
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'src="data:{mime};base64,{b64}"'
    return re.sub(r'src="(img/[^"]+)"', repl, main_html)

def clean(main_html):
    # quita los botones de "swap image" (solo del editor)
    h = re.sub(r'<button class="swap"[^>]*>.*?</button>', '', main_html, flags=re.S)
    h = re.sub(r'\sloading="lazy"', '', h)
    return h

def extract_unit(path):
    src = path.read_text(encoding="utf-8")
    title = re.search(r'<title>(.*?)</title>', src, re.S).group(1).strip()
    title = re.sub(r'\s*—\s*MTA\s*$', '', title)
    main = re.search(r'<main>(.*?)</main>', src, re.S).group(1)
    return title, clean(embed_images(main))

def page(title, body, lang="en"):
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{H.escape(title)}</title><style>{CSS}</style></head><body>\n{body}\n</body></html>')

MANIFEST = ('<?xml version="1.0" encoding="UTF-8"?>\n'
 '<manifest identifier="MAN-mta-{ident}" version="1.1"\n'
 '  xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"\n'
 '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
 '  xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd">\n'
 '  <organizations default="ORG">\n    <organization identifier="ORG">\n'
 '      <title>{org_title}</title>\n{items}\n    </organization>\n  </organizations>\n'
 '  <resources>\n{resources}\n  </resources>\n</manifest>\n')

def write_pkg(zname, ident, org_title, pages):
    """pages: lista de (item_title, filename, html)."""
    items = "\n".join(
        f'      <item identifier="IT{i}" identifierref="R{i}"><title>{H.escape(t)}</title></item>'
        for i, (t, f, h) in enumerate(pages, 1))
    resources = "\n".join(
        f'    <resource identifier="R{i}" type="webcontent" href="{f}"><file href="{f}"/></resource>'
        for i, (t, f, h) in enumerate(pages, 1))
    man = MANIFEST.format(ident=ident, org_title=H.escape(org_title), items=items, resources=resources)
    zpath = OUT / zname
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("imsmanifest.xml", man)
        for t, f, h in pages:
            z.writestr(f, h)
    print(f"{zname}  ({zpath.stat().st_size//1024} KB, {len(pages)} item)")

def build_unit(n):
    title, body = extract_unit(DOCS / f"unit{n}.html")
    html = page(title, body)
    write_pkg(f"IMSCP-unit{n}.zip", f"unit{n}", title, [(title, f"unit{n}.html", html)])

def build_guide():
    """Planificador de sesiones como recurso OCULTO de profesor."""
    src = (DOCS / "admin" / "index.html").read_text(encoding="utf-8")
    # ya es una página autónoma; la metemos tal cual (enlaza a la web por URL absoluta)
    write_pkg("IMSCP-teacher-guide.zip", "teacher-guide",
              "MTA — Session plan (TEACHER · hidden)",
              [("Session-by-session plan (teacher)", "session-plan.html", src)])

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "1"
    if arg == "guide":
        build_guide()
    elif arg == "all":
        for n in range(1, 8):
            build_unit(n)
    else:
        build_unit(int(arg))
