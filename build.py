#!/usr/bin/env python3
"""
MTA — Audiovisual and Scenic Technical Means
Reconstruye el libro (PDF con OCR) como sitio web estatico.

Fase 1: libro fiel (texto + imagenes + cajas pedagogicas propias + indice + buscador).
Los estados visuales 'update' (novedades 2026) y 'legacy' ya estan soportados en el
CSS y en el modelo de datos; se rellenaran en la Fase 3 desde overlays/*.json.

Uso:  .venv/bin/python build.py
"""
import fitz, os, json, re, html, hashlib, glob

SRC = "/Users/ondarru/Library/CloudStorage/Dropbox/1 HEZKUNTZA/0 TARTANGA/2025-2026/1 RPA/1 MTA/PDF Audiovisual and Scenic Technical Means"
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "docs")     # GitHub Pages sirve desde main /docs
IMG  = os.path.join(SITE, "img")
CNAME_DOMAIN = "mta.cinemafilmak.com"  # subdominio en cinemafilmak.com

# unidad -> (fichero PDF, titulo corto para menu)
UNITS = [
    ("unit1", "UNIT1_The Image.pdf", "The Image"),
    ("unit2", "UNIT2_Lighting.pdf", "Lighting"),
    ("unit3", "UNIT3_Sound.pdf", "Sound"),
    ("unit4", "UNIT4_Multicam.pdf", "Multicam"),
    ("unit5", "UNIT5_Post-production equipment in audiovisual projects.pdf", "Post-production"),
    ("unit6", "UNIT6_TECHNICAL EQUIPMENT IN  MULTIMEDIA PROJECTS.pdf", "Multimedia"),
    ("unit7", "UNIT7_TRANSMITTING AND BROADCASTING SYSTEM.pdf", "Transmitting & Broadcasting"),
]

CALLOUTS = {
    "REMEMBER!":            ("remember", "\U0001F9E0", "Remember"),
    "PROFESSIONAL ADVICE!": ("advice",   "\U0001F393", "Professional advice"),
    "ACTIVITY":             ("activity", "✏️", "Activity"),
    "LET'S PRACTICE!":      ("practice", "\U0001F6E0️", "Let's practice"),
    "LET’S PRACTICE!": ("practice", "\U0001F6E0️", "Let's practice"),
    "WATCH THIS VIDEO:":    ("video",    "▶️", "Watch this video"),
    "WATCH THIS VIDEO":     ("video",    "▶️", "Watch this video"),
}

def callout_of(txt):
    u = txt.strip().upper()
    for k, v in CALLOUTS.items():
        if u.startswith(k):
            return k, v
    return None

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:48]

def classify(size):
    if size >= 24:   return "h1"
    if size >= 15.5: return "h2"
    if size >= 13.5: return "h3"
    return "p"

# ---------------------------------------------------------------- extract
def clean_text(s):
    # quita glifos de area privada (bullets/iconos OCR) y normaliza espacios
    s = "".join(ch for ch in s if not (0xE000 <= ord(ch) <= 0xF8FF))
    s = s.replace("", "").replace("□", "").replace("", "")
    return re.sub(r'[ \t]+', ' ', s).strip()

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', s.lower())

def extract(slug, pdf):
    path = os.path.join(SRC, pdf)
    d = fitz.open(path)
    imgdir = os.path.join(IMG, slug)
    os.makedirs(imgdir, exist_ok=True)
    for f in glob.glob(os.path.join(imgdir, "*")):
        os.remove(f)

    # --- pasada 1: recopila lineas de margen para detectar cabeceras/pies repetidos ---
    margin_count = {}
    npages = d.page_count
    for p in d:
        ph = p.rect.height
        for b in p.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b["lines"]:
                txt = clean_text("".join(s["text"] for s in l["spans"]))
                if not txt:
                    continue
                rel = l["bbox"][1] / ph
                if rel < 0.08 or rel > 0.92:          # zona de cabecera/pie
                    margin_count[norm(txt)] = margin_count.get(norm(txt), 0) + 1
    repeated = {k for k, c in margin_count.items() if c >= max(3, npages * 0.3) and k}

    def is_chrome(txt, rel):
        n = norm(txt)
        if not n:
            return True
        if (rel < 0.08 or rel > 0.92):
            if n in repeated:
                return True
            if re.fullmatch(r'\d{1,3}', txt.strip()):   # numero de pagina suelto
                return True
        return False

    # --- pasada 2: extrae contenido conservando limites de bloque (parrafos) ---
    elements, seen = [], set()
    for pi, p in enumerate(d):
        ph = p.rect.height
        items = []   # (y, x, kind, data, block_id)
        for bi, b in enumerate(p.get_text("dict")["blocks"]):
            x0, y0, x1, y1 = b["bbox"]
            if b.get("type") == 0:
                for l in b["lines"]:
                    raw = "".join(s["text"] for s in l["spans"])
                    txt = clean_text(raw)
                    if not txt:
                        continue
                    rel = l["bbox"][1] / ph
                    if is_chrome(txt, rel):
                        continue
                    size = max((s["size"] for s in l["spans"]), default=0)
                    items.append((l["bbox"][1], l["bbox"][0], "text",
                                  {"size": size, "txt": txt,
                                   "y0": l["bbox"][1], "y1": l["bbox"][3]}, (pi, bi)))
            elif b.get("type") == 1:
                img = b.get("image")
                if not img:
                    continue
                w, h = x1 - x0, y1 - y0
                if w < 45 or h < 45:
                    continue
                hsh = hashlib.md5(img).hexdigest()[:10]
                ext = b.get("ext", "png")
                fname = f"{slug}_{hsh}.{ext}"
                if hsh not in seen:
                    with open(os.path.join(imgdir, fname), "wb") as fh:
                        fh.write(img)
                    seen.add(hsh)
                items.append((y0, x0, "img",
                              {"file": f"img/{slug}/{fname}", "w": round(w), "h": round(h)},
                              (pi, bi)))
        items.sort(key=lambda t: (round(t[0] / 6), t[1]))
        for _, _, kind, data, blk in items:
            if kind == "text":
                elements.append({"t": classify(round(data["size"], 1)),
                                 "txt": data["txt"], "pg": pi + 1, "blk": blk,
                                 "y0": data["y0"], "y1": data["y1"], "sz": data["size"]})
            else:
                elements.append({"t": "img", "file": data["file"],
                                 "w": data["w"], "h": data["h"], "pg": pi + 1, "blk": blk})
    d.close()
    return elements

# ---------------------------------------------------------------- render
def render_unit(slug, elements, short, corr=None):
    corr = corr or []
    frag, toc = [], []
    buf = []
    in_call = None
    call_buf = []
    title_parts = []
    fig_n = 0
    cur_blk = None
    prev_y1 = None
    prev_pg = None

    def fix(s):
        return apply_corrections(s, corr) if corr else s

    def flush_para():
        if buf:
            frag.append(f'<p>{html.escape(fix(" ".join(buf).strip()))}</p>')
            buf.clear()

    def flush_call():
        nonlocal in_call
        if in_call:
            cls, icon, label = in_call
            body = "".join(f"<p>{html.escape(fix(x))}</p>" for x in call_buf if x.strip())
            frag.append(f'<div class="callout {cls}"><div class="callout-h">{icon} {label}</div>{body}</div>')
            call_buf.clear()
            in_call = None

    # --- pre-pasada: titulo = lineas h1 consecutivas al inicio de la pag 1 ---
    for e in elements:
        if e["t"] == "img":
            continue
        if e["t"] == "h1" and e.get("pg") == 1 and (e["txt"].upper().startswith("UNIT") or title_parts):
            title_parts.append(e["txt"])
        elif title_parts:
            break
        elif e.get("pg", 1) > 1:
            break

    last_was_heading = False
    for e in elements:
        t = e["t"]
        txt = e["txt"] if t != "img" else ""
        up = txt.upper()

        # pagina 1 = portada + indice: se descarta por completo (el titulo lo ponemos aparte)
        if e.get("pg") == 1:
            continue

        if t == "img":
            flush_para(); flush_call(); last_was_heading = False
            fig_n += 1
            frag.append(
                f'<figure data-fig="{fig_n}"><img loading="lazy" src="{e["file"]}" alt="">'
                f'<figcaption><span>Fig. {fig_n}</span>'
                f'<button class="swap" data-fig="{fig_n}">swap image</button></figcaption></figure>')
            continue

        co = callout_of(txt)
        if co:
            flush_para(); flush_call(); last_was_heading = False
            k, v = co
            in_call = v
            rest = txt[len(k):].strip(" :")
            if rest:
                call_buf.append(rest)
            continue

        if t in ("h2", "h3"):
            # fórmulas / restos matemáticos colados como "encabezado" -> tratar como texto
            has_ascii_alpha = re.search(r'[A-Za-z]{2,}', txt)
            has_math = ('=' in txt) or any(0x1D400 <= ord(c) <= 0x1D7FF for c in txt)
            if has_math or not has_ascii_alpha:
                last_was_heading = False
                if in_call is not None:
                    call_buf.append(txt)
                else:
                    buf.append(txt)
                    cur_blk = e.get("blk"); prev_y1 = e.get("y1"); prev_pg = e.get("pg")
                continue
            # linea de continuacion de un titulo (no empieza por numero) -> unir al anterior
            if last_was_heading and not re.match(r'^\d', txt) and frag and frag[-1].startswith("<h"):
                tag = frag[-1][1:3]  # h2 / h3
                inner = re.sub(r'</h[23]>$', '', frag[-1])
                frag[-1] = inner + " " + html.escape(fix(txt)) + f"</{tag}>"
                continue
            flush_para(); flush_call()
            if up.strip() == "CONTENTS":
                continue
            lvl = 2 if t == "h2" else 3
            sid = slugify(txt)                 # ancla desde el texto original (estable)
            disp = fix(txt)
            if lvl == 2 and re.match(r'^\d+\.\d', txt):
                toc.append((sid, disp))
            frag.append(f'<h{lvl} id="{sid}">{html.escape(disp)}</h{lvl}>')
            last_was_heading = True
            continue

        # parrafo normal
        last_was_heading = False
        if in_call is not None:
            call_buf.append(txt)
        else:
            # nuevo parrafo si: cambia de pagina, o hueco vertical grande, o salto de bloque con hueco
            gap_break = False
            if buf:
                if prev_pg is not None and e.get("pg") != prev_pg:
                    gap_break = True
                elif prev_y1 is not None and e.get("y0") is not None:
                    gap = e["y0"] - prev_y1
                    if gap > 0.55 * max(e.get("sz", 12), 8):
                        gap_break = True
            if gap_break:
                flush_para()
            buf.append(txt)
            cur_blk = e.get("blk")
            prev_y1 = e.get("y1")
            prev_pg = e.get("pg")
    flush_para(); flush_call()

    title = ""
    for part in title_parts:
        part = part.strip()
        if title.endswith("-"):
            title = title[:-1] + part
        else:
            title += ((" " if title else "") + part)
    title = re.sub(r'\s+', ' ', title).strip() or f"Unit — {short}"
    # inserta espacio tras 'UNIT n:' si falta (ej. 'UNIT 5:POST')
    title = re.sub(r'(UNIT\s*\d+:)(\S)', r'\1 \2', title)
    title = fix(title)
    frag.insert(0, f'<h1>{html.escape(title)}</h1>')
    return title, toc, frag

# ---------------------------------------------------------------- deck (slides)
# Material complementario en formato diapositivas (p.ej. Unit2_ THE LIGHT SOURCES.pdf).
# Se integra dentro de una unidad como seccion propia, atribuida y con distintivo.
DECKS = {
    "unit2": {
        "pdf": "Unit2_ THE LIGHT SOURCES.pdf",
        "slug": "unit2-lightsources",
        "title": "The Light Sources",
        "author": "Mercedes González",
        "anchor": "light-sources-deck",
        "after": "2.3",      # se integra dentro del punto 2.3 (su tema natural)
    },
}

def extract_deck(cfg):
    path = os.path.join(SRC, cfg["pdf"])
    d = fitz.open(path)
    slug = cfg["slug"]
    imgdir = os.path.join(IMG, slug)
    os.makedirs(imgdir, exist_ok=True)
    for f in glob.glob(os.path.join(imgdir, "*")):
        os.remove(f)

    slides, seen = [], set()
    for pi, p in enumerate(d):
        if pi == 0:
            continue  # portada del deck
        ph, pw = p.rect.height, p.rect.width
        # links de la pagina: rect -> uri
        links = [(l["from"], l["uri"]) for l in p.get_links() if l.get("uri")]

        lines, imgs = [], []
        for b in p.get_text("dict")["blocks"]:
            x0, y0, x1, y1 = b["bbox"]
            if b.get("type") == 0:
                for l in b["lines"]:
                    txt = clean_text("".join(s["text"] for s in l["spans"]))
                    if not txt:
                        continue
                    if l["bbox"][1] / ph > 0.9:      # barra de pie repetida
                        continue
                    size = max((s["size"] for s in l["spans"]), default=0)
                    # uri si esta linea cae sobre un link
                    uri = None
                    lr = fitz.Rect(l["bbox"])
                    for rect, u in links:
                        if fitz.Rect(rect).intersects(lr):
                            uri = u; break
                    lines.append({"y": l["bbox"][1], "size": size, "txt": txt, "uri": uri})
            elif b.get("type") == 1:
                img = b.get("image")
                if not img:
                    continue
                w, h = x1 - x0, y1 - y0
                if w < 80 or h < 80:
                    continue
                hsh = hashlib.md5(img).hexdigest()[:10]
                ext = b.get("ext", "png")
                fname = f"{slug}_{hsh}.{ext}"
                if hsh not in seen:
                    with open(os.path.join(imgdir, fname), "wb") as fh:
                        fh.write(img)
                    seen.add(hsh)
                imgs.append({"y": y0, "file": f"img/{slug}/{fname}"})
        lines.sort(key=lambda l: l["y"])
        if not lines and not imgs:
            continue
        # titulo del slide = primera linea grande; resto = cuerpo
        title = ""
        body = lines
        if lines and lines[0]["size"] >= 20:
            cand = lines[0]["txt"].strip()
            # ignora "titulos" que son solo un numero o demasiado cortos
            if len(cand) >= 4 and not re.fullmatch(r'\d+[.)]?', cand):
                title = cand
                body = lines[1:]
        slides.append({"n": pi + 1, "title": title, "body": body,
                       "imgs": [im["file"] for im in sorted(imgs, key=lambda i: i["y"])]})
    d.close()
    return slides

def render_deck(cfg, slides, corr=None):
    corr = corr or []
    def fix(s):
        return apply_corrections(s, corr) if corr else s
    aid = cfg["anchor"]
    out = [f'<section class="deck" id="{aid}">',
           '<div class="deck-tag">◈ Classroom material</div>',
           f'<h2 style="scroll-margin-top:16px">Complementary: {html.escape(cfg["title"])}</h2>',
           f'<p class="deck-credit">Slide deck by {html.escape(cfg["author"])} — integrated here as '
           f'complementary material to the book\'s lighting chapter.</p>']
    last_title = None
    for s in slides:
        out.append('<div class="slide">')
        if s["title"] and s["title"] != last_title:
            out.append(f'<h3>{html.escape(fix(s["title"]))}</h3>')
            last_title = s["title"]
        # cuerpo: corrige el texto unido y re-inserta los enlaces por su texto ancla
        body_txt = fix(" ".join(l["txt"] for l in s["body"]).strip())
        if body_txt:
            html_body = html.escape(body_txt)
            for l in s["body"]:
                if l["uri"]:
                    anchor = html.escape(l["txt"])
                    link = (f'<a href="{html.escape(l["uri"])}" target="_blank" '
                            f'rel="noopener">{anchor}</a>')
                    html_body = html_body.replace(anchor, link, 1)
            out.append("<p>" + html_body + "</p>")
        for f in s["imgs"]:
            out.append(f'<figure class="slide-fig"><img loading="lazy" src="{f}" alt="">'
                       f'<figcaption><button class="swap">swap image</button></figcaption></figure>')
        out.append('</div>')
    out.append('</section>')
    return "\n".join(out)

# ---------------------------------------------------------------- overlays (Update 2026 / Legacy)
OVERLAYS = os.path.join(HERE, "overlays")

def render_overlay_block(entry):
    kind = entry.get("kind", "update")
    if kind == "update":
        tag = "◆ Update · 2026"
        cls = "update"
    else:
        tag = "▽ Legacy"
        cls = "legacy"
    parts = [f'<div class="block {cls}">', f'<div class="block-tag">{tag}</div>']
    if entry.get("title"):
        parts.append(f'<h3>{html.escape(entry["title"])}</h3>')
    for p in entry.get("paras", []):
        parts.append(f'<p>{p}</p>')          # el texto del overlay puede traer <a>, <b>...
    srcs = entry.get("sources", [])
    if srcs:
        links = " · ".join(
            f'<a href="{html.escape(s["url"])}" target="_blank" rel="noopener">{html.escape(s["label"])}</a>'
            for s in srcs)
        parts.append(f'<p class="sources">Sources: {links}</p>')
    parts.append('</div>')
    return "\n".join(parts)

def load_overlays(slug):
    path = os.path.join(OVERLAYS, f"{slug}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

# ---- correcciones de texto (sobreviven a los rebuilds) ----
CORRECTIONS = os.path.join(HERE, "corrections")

def load_corrections(slug):
    path = os.path.join(CORRECTIONS, f"{slug}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

def apply_corrections(text, corr):
    for c in corr:
        if c.get("find"):
            text = text.replace(c["find"], c.get("replace", ""))
    return text

# ---- reemplazo permanente de fotos (desde el JSON exportado por el editor) ----
def apply_photo_overrides():
    import base64
    path = os.path.join(HERE, "photo-overrides.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        overrides = json.load(f)   # { "img/unitX/....jpeg": "data:image/...;base64,...." }
    n = 0
    for rel, data in overrides.items():
        target = os.path.join(SITE, rel)
        if not os.path.isabs(target) and os.path.normpath(SITE) not in os.path.normpath(target):
            continue  # seguridad: solo dentro de site/
        m = re.match(r'data:image/[\w.+-]+;base64,(.*)$', data, re.S)
        if not m or not os.path.exists(os.path.dirname(target)):
            continue
        with open(target, "wb") as fh:
            fh.write(base64.b64decode(m.group(1)))
        n += 1
    if n:
        print(f"photo overrides applied: {n} image(s) replaced")

def h2_id_indices(frag):
    return [i for i, s in enumerate(frag) if s.startswith('<h2 id="')]

def heading_text(s):
    m = re.search(r'>([^<]+)</h2>', s)
    return m.group(1) if m else ""

def inject_after_section(frag, after, block_html):
    """Inserta block_html al final de la seccion cuyo titulo empieza por `after`
    (p.ej. '2.3'); si after=='end' o no se encuentra, al final del cuerpo."""
    if after == "end":
        frag.append(block_html); return
    idxs = h2_id_indices(frag)
    target = None
    for i in idxs:
        if re.match(r'\s*' + re.escape(after) + r'\b', heading_text(frag[i])):
            target = i; break
    if target is None:
        frag.append(block_html); return
    nxt = next((i for i in idxs if i > target), None)
    frag.insert(nxt if nxt is not None else len(frag), block_html)

# ---------------------------------------------------------------- html shell
def page_shell(title, unit_nav, toc_html, body, active, search=False):
    search_ui = ('<div class="search"><input id="q" type="search" '
                 'placeholder="Search the book…" autocomplete="off">'
                 '<div id="results"></div></div>') if search else ""
    return f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — MTA</title>
<link rel="stylesheet" href="assets/style.css">
</head><body>
<div class="wrap">
<aside>
  <a class="brand" href="index.html">MTA</a>
  <div class="book">Audiovisual &amp; Scenic Technical Means</div>
  {search_ui}
  <nav class="units">{unit_nav}</nav>
  <div class="legend">
    <span><i class="dot book"></i>Book</span>
    <span><i class="dot upd"></i>Update 2026</span>
    <span><i class="dot leg"></i>Legacy</span>
  </div>
  <button id="editToggle" class="edit-toggle">✎ Edit photos</button>
  {('<nav class="toc"><div class="toc-h">On this page</div>'+toc_html+'</nav>') if toc_html else ''}
</aside>
<main>{body}</main>
</div>
<aside id="edits-panel" class="edits-panel">
  <div class="edits-head">Photo edits (<span id="edits-count">0</span>)</div>
  <div class="pub-row">
    <button id="edits-publish" class="pub">Publish to web</button>
    <button id="edits-token" class="tok">Set GitHub token…</button>
    <button id="edits-export" class="tok">Export JSON</button>
  </div>
  <p id="pub-status" class="pub-status"></p>
  <div id="edits-list"></div>
  <p class="muted small">“Publish to web” commits your photo changes straight to the site (rebuilds in ~1 min). The token stays only in this browser. “Export JSON” just downloads the edits.</p>
</aside>
<script src="assets/search.js" defer></script>
<script src="assets/editor.js" defer></script>
</body></html>'''

def unit_nav(active):
    out = []
    for i, (slug, _, short) in enumerate(UNITS, 1):
        cls = ' class="active"' if slug == active else ""
        out.append(f'<a href="{slug}.html"{cls}><b>{i}</b> {html.escape(short)}</a>')
    return "\n".join(out)

# ---------------------------------------------------------------- main
def main():
    os.makedirs(SITE, exist_ok=True)
    search_index = []
    index_cards = []
    for slug, pdf, short in UNITS:
        els = extract(slug, pdf)
        corr = load_corrections(slug)          # correcciones de texto (proofreading)
        title, toc, frag = render_unit(slug, els, short, corr)
        if corr:
            print(f"   + corrections: {len(corr)} rule(s)")

        # --- novedades Update 2026 / Legacy (overlays editables) ---
        overlay_entries = load_overlays(slug)
        n_upd = n_leg = 0
        for entry in overlay_entries:
            inject_after_section(frag, entry.get("after", "end"), render_overlay_block(entry))
            if entry.get("kind", "update") == "legacy":
                n_leg += 1
            else:
                n_upd += 1

        # --- material complementario (deck) integrado en su seccion ---
        if slug in DECKS:
            cfg = DECKS[slug]
            slides = extract_deck(cfg)
            deck_corr = load_corrections(cfg["slug"])
            inject_after_section(frag, cfg.get("after", "end"), render_deck(cfg, slides, deck_corr))
            if deck_corr:
                print(f"     deck corrections: {len(deck_corr)} rule(s)")
            # entrada en el TOC, justo tras su seccion
            entry = (cfg["anchor"], f'★ {cfg["title"]} (complementary)')
            pos = next((k + 1 for k, (sid, t) in enumerate(toc)
                        if re.match(r'\s*' + re.escape(cfg.get("after", "")) + r'\b', t)), len(toc))
            toc.insert(pos, entry)
            print(f"   + deck '{cfg['title']}': {len(slides)} slides @ {cfg.get('after')}")
        if overlay_entries:
            print(f"   + overlays: {n_upd} update, {n_leg} legacy")

        body = "\n".join(frag)
        toc_html = "\n".join(f'<a href="#{sid}">{html.escape(t)}</a>' for sid, t in toc)
        page = page_shell(title, unit_nav(slug), toc_html, body, slug, search=True)
        with open(os.path.join(SITE, f"{slug}.html"), "w") as f:
            f.write(page)
        n_fig = body.count("<figure")
        print(f"{slug}: '{title[:48]}'  {len(toc)} sections, {n_fig} figures")
        # buscador
        for sid, t in toc:
            search_index.append({"u": slug, "t": t, "a": sid, "title": short})
        # tarjeta indice
        secs = "".join(f"<li><a href='{slug}.html#{sid}'>{html.escape(t)}</a></li>" for sid, t in toc)
        num = slug.replace("unit", "")
        index_cards.append(
            f"<article class='card'><a class='card-h' href='{slug}.html'>"
            f"<span class='num'>{num}</span><span>{html.escape(title)}</span></a>"
            f"<ul>{secs}</ul></article>")

    with open(os.path.join(SITE, "assets", "search-index.json"), "w") as f:
        json.dump(search_index, f, ensure_ascii=False)

    # index.html
    idx_body = ("<header class='hero'><h1>Audiovisual &amp; Scenic Technical Means</h1>"
                "<p class='sub'>Technical means for audiovisual and scenic media — "
                "the full course book, online, updated for 2026.</p>"
                "<div class='legend big'>"
                "<span><i class='dot book'></i>Original book</span>"
                "<span><i class='dot upd'></i>Update 2026 (added)</span>"
                "<span><i class='dot leg'></i>Legacy</span></div></header>"
                "<section class='grid'>" + "".join(index_cards) + "</section>")
    idx = page_shell("Contents", unit_nav(""), "", idx_body, "", search=True)
    with open(os.path.join(SITE, "index.html"), "w") as f:
        f.write(idx)

    apply_photo_overrides()   # reemplazos permanentes de foto, si hay JSON exportado
    with open(os.path.join(SITE, "CNAME"), "w") as f:   # dominio para GitHub Pages
        f.write(CNAME_DOMAIN + "\n")
    with open(os.path.join(SITE, ".nojekyll"), "w") as f:   # sirve carpetas con _ tal cual
        f.write("")
    print(f"\nindex.html + {len(UNITS)} units + search index + CNAME -> {SITE}")

if __name__ == "__main__":
    main()
