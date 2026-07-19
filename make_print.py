#!/usr/bin/env python3
"""
Genera un PDF de imprenta (A4, color, tipo apuntes) de una unidad,
reutilizando el mismo contenido del sitio (texto corregido + novedades + deck).

Uso:  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python make_print.py unit2
"""
import sys, os, html
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("build", os.path.join(HERE, "build.py"))
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)

PRINT_CSS = """
@page {
  size: A4;
  margin: 20mm 18mm 20mm 18mm;
  @top-right { content: string(runhead); font-size: 8.5pt; color: #b0aaa0; }
  @bottom-center { content: counter(page); font-size: 9pt; color: #8a8378; }
}
@page :first { @top-right { content: none; } }
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2328;
       font-size: 10.5pt; line-height: 1.5; }
h1 { string-set: runhead content(); font-size: 24pt; line-height: 1.15;
     color: #1f2328; margin: 0 0 6pt; padding: 0 0 10pt 0;
     border-bottom: 3pt solid #b23b2e; }
.chapline { color:#b23b2e; font-weight:700; font-size:10pt; letter-spacing:.08em;
            text-transform:uppercase; margin-bottom:4pt; }
h2 { font-size: 15pt; margin: 18pt 0 5pt; color:#1f2328; break-after: avoid; }
h3 { font-size: 12pt; margin: 12pt 0 3pt; color:#33383e; break-after: avoid; }
p  { margin: 0 0 7pt; text-align: justify; }
a  { color: #0f766e; text-decoration: none; }
figure { margin: 10pt 0; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 15cm; border: 0.5pt solid #e6e3dd; border-radius: 4pt; }
figcaption { font-size: 8pt; color: #6b7280; margin-top: 3pt; }
.swap { display: none; }               /* botón sólo de la web */
/* cajas pedagógicas del libro */
.callout { border-left: 3pt solid #c9c4ba; padding: 6pt 9pt; margin: 8pt 0;
           background:#f7f6f3; break-inside: avoid; border-radius:0 4pt 4pt 0; }
.callout-h { font-weight:700; font-size:8.5pt; text-transform:uppercase; letter-spacing:.03em; margin-bottom:2pt; }
.callout p { font-size: 9.5pt; margin: 2pt 0; }
.callout.remember{border-color:#2563eb;background:#f2f6ff}
.callout.advice{border-color:#7c3aed;background:#f7f3ff}
.callout.activity{border-color:#059669;background:#eefcf5}
.callout.practice{border-color:#d97706;background:#fff7ed}
.callout.video{border-color:#dc2626;background:#fef4f4}
/* añadidos nuestros */
.block { border-radius: 6pt; padding: 9pt 12pt; margin: 10pt 0; break-inside: avoid; }
.block .block-tag { display:inline-block; font-size:8pt; font-weight:700; letter-spacing:.05em;
     text-transform:uppercase; padding:2pt 7pt; border-radius:10pt; margin-bottom:4pt; }
.block h3 { margin: 1pt 0 4pt; }
.block.update { background:#ecfdf9; border:0.5pt solid #bfe9e2; }
.block.update .block-tag { background:#0f766e; color:#fff; }
.block.update h3 { color:#0f766e; }
.block.legacy { background:#f7f2e7; border:0.5pt dashed #d8c9a6; }
.block.legacy .block-tag { background:#8a6d3b; color:#fff; }
.block.legacy p { color:#5f533a; }
.block p.sources { font-size:8.5pt; opacity:.85; }
/* deck complementario */
.deck { border:0.5pt solid #cdd6ee; border-radius:7pt; background:#f6f8ff; padding:10pt 12pt; margin:14pt 0; }
.deck .deck-tag { display:inline-block; font-size:8pt; font-weight:700; letter-spacing:.05em;
     text-transform:uppercase; padding:2pt 7pt; border-radius:10pt; margin-bottom:4pt; background:#4f46e5; color:#fff; }
.deck h2 { color:#3730a3; margin:3pt 0 2pt; border:0; }
.deck h3 { color:#3730a3; }
.deck .deck-credit { font-size:9pt; color:#6b7280; margin:0 0 4pt; }
.deck .slide-fig img { max-width: 70%; }
"""

def build_unit_body(slug):
    unit = next(u for u in build.UNITS if u[0] == slug)
    _, pdf, short = unit
    els = build.extract(slug, pdf)
    corr = build.load_corrections(slug)
    title, toc, frag = build.render_unit(slug, els, short, corr)
    for entry in build.load_overlays(slug):
        build.inject_after_section(frag, entry.get("after", "end"), build.render_overlay_block(entry))
    if slug in build.DECKS:
        cfg = build.DECKS[slug]
        slides = build.extract_deck(cfg)
        dc = build.load_corrections(cfg["slug"])
        build.inject_after_section(frag, cfg.get("after", "end"), build.render_deck(cfg, slides, dc))
    # inserta la línea de capítulo antes del h1
    num = slug.replace("unit", "")
    frag[0] = f'<div class="chapline">Unit {num} · Audiovisual &amp; Scenic Technical Means</div>' + frag[0]
    return title, "\n".join(frag)

def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "unit2"
    title, body = build_unit_body(slug)
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<style>{PRINT_CSS}</style></head><body>{body}</body></html>')
    out_html = os.path.join(HERE, "print", f"{slug}_print.html")
    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    open(out_html, "w").write(doc)
    from weasyprint import HTML
    out_pdf = os.path.join(HERE, "print", f"{slug}_print.pdf")
    HTML(string=doc, base_url=build.SITE).write_pdf(out_pdf)
    print(f"{slug}: '{title}' -> {out_pdf} ({os.path.getsize(out_pdf)//1024} KB)")

if __name__ == "__main__":
    main()
