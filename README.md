# MTA — Audiovisual & Scenic Technical Means (web del libro)

Reconstrucción del libro (PDF con OCR, 7 units, inglés) como sitio web estático,
para publicar dentro de Cinemafilmak. Las novedades que añadimos se marcan
visualmente para no confundirlas con el texto original.

## Estados visuales
- **Libro** — texto original, sin marca.
- **Update 2026** — caja verde con etiqueta: lo que añadimos nosotros (novedad actual).
- **Legacy** — caja ocre punteada: técnica del libro que hoy es histórica.

## Estructura
```
build.py              generador (PyMuPDF): PDF -> site/
site/
  index.html          portada + índice de las 7 units
  unit1..7.html       una página por unidad (índice lateral + buscador)
  assets/style.css    estilos compartidos
  assets/search.js    buscador cliente
  assets/search-index.json
  img/unitN/          imágenes extraídas del PDF
```

## Regenerar el sitio
```
.venv/bin/python build.py
```

## Ver en local
```
cd site && ../.venv/bin/python -m http.server 8850
# abrir http://localhost:8850
```

## Añadir un tema nuevo o una novedad (Update 2026 / Legacy)
Editar `overlays/<unit>.json` y añadir una entrada:
```json
{
  "after": "1.4",                       // nº de sección tras la que aparece
  "kind": "update",                     // "update" (verde) o "legacy" (ocre)
  "title": "Título del bloque",
  "paras": ["Texto con <b>negritas</b> y <a href='...'>enlaces</a>."],
  "sources": [{"label":"Fuente","url":"https://..."}]
}
```
Después `.venv/bin/python build.py`. No toca el texto del libro.

## Corregir texto del libro (typos del OCR, cambios)
Editar `corrections/<unit>.json` con reglas buscar→reemplazar (sobreviven a los rebuilds):
```json
[ { "find": "texto tal cual está", "replace": "texto correcto", "note": "por qué" } ]
```

## Editar/sustituir fotos
- **Web pública:** no muestra ningún control de edición.
- **Modo privado:** abrir la página con `?edit` (p.ej. `unit1.html?edit`). Aparece el botón
  **“Edit photos”** → cada figura muestra *swap*, eliges un archivo (foto mejor o del libro físico),
  se guarda en el navegador y aparece en el panel lateral. **Export JSON** descarga `mta-photo-overrides.json`.
- **Hacerlo permanente:** copiar ese archivo a la raíz del proyecto como `photo-overrides.json` y
  ejecutar `build.py`; las imágenes quedan reemplazadas de forma definitiva (a prueba de rebuilds).

## Pendiente / polish
- Restos del OCR original (frases duplicadas puntuales, títulos de vídeos incrustados como encabezado).
- Integración final dentro de Cinemafilmak.
