"""Tarjetas por escena con el estilo Millón X (1080x1920).

Uso como script::

    python -m app.branding.cards escenas.json salida_dir

``escenas.json``: lista de escenas ``{"accent": "red", "kicker": "$ANT · IPO",
"lines": [["-80.700 M$", 190, "red", 60], ["EN 6 MESES", 130, "white", 0]]}``.
Cada línea es ``[texto, tamaño_max, color, separación_inferior]``.
"""
from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.branding.millonx import ACCENTS, BG, BODY_FONT, GREY, HANDLE, HEADLINE_FONT, NAVY, ORANGE, WHITE, font_path

W, H = 1080, 1920
MAX_W = 940


def _color(c):
    return ACCENTS[c] if isinstance(c, str) else tuple(c)


def _body(size):
    f = ImageFont.truetype(font_path(BODY_FONT), size)
    try:
        f.set_variation_by_name("ExtraBold")
    except Exception:
        pass
    return f


def _fit(text, maxsize):
    s = maxsize
    while True:
        f = ImageFont.truetype(font_path(HEADLINE_FONT), s)
        if f.getlength(text) <= MAX_W or s < 30:
            return f
        s -= 4


def background(accent, kicker=""):
    im = Image.new("RGB", (W, H), BG)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([-300, -200, 900, 800], fill=accent + (70,))
    d.ellipse([400, 1100, 1500, 2200], fill=accent + (40,))
    lay = lay.filter(ImageFilter.GaussianBlur(160))
    im.paste(lay, (0, 0), lay)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 14], fill=accent)
    if kicker:
        d.text((70, 90), kicker.upper(), font=_body(34), fill=GREY)
    # firma de marca abajo, fuera de la zona de subtítulos
    f = _body(32)
    # firma: "MILLÓN" blanco + "X" naranja llama + handle de X, sobre pastilla marino
    d.rounded_rectangle([50, H - 130, W - 50, H - 60], radius=35, fill=NAVY)
    x, y = 85, H - 115
    d.text((x, y), "MILLÓN", font=f, fill=WHITE)
    x += f.getlength("MILLÓN ")
    d.text((x, y), "X", font=f, fill=ORANGE)
    hf = _body(30)
    d.text((W - 85 - hf.getlength(HANDLE), y + 2), HANDLE, font=hf, fill=GREY)
    return im


def render(path, accent, lines, kicker="", top=None):
    accent = _color(accent)
    im = background(accent, kicker)
    d = ImageDraw.Draw(im)
    items = [(t, _fit(t, sz), _color(c), gap) for t, sz, c, gap in lines]
    hs = [f.getbbox(t)[3] - f.getbbox(t)[1] for t, f, _, _ in items]
    total = sum(hs) + sum(g for *_, g in items[:-1])
    # bloque centrado en el tercio superior-medio: deja el 75-92 % libre para subtítulos
    y = top if top else (1300 - total) // 2 + 100
    for (t, f, c, _g), h in zip(items, hs):
        bb = f.getbbox(t)
        x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        d.text((x + 5, y - bb[1] + 6), t, font=f, fill=(0, 0, 0))
        d.text((x, y - bb[1]), t, font=f, fill=c)
        y += h + _g
    im.save(path)
    return path


def render_scenes(scenes, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, s in enumerate(scenes, 1):
        p = os.path.join(out_dir, f"card{i:02d}.png")
        render(p, s.get("accent", "orange"), s["lines"], s.get("kicker", ""))
        paths.append(p)
    return paths


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as fh:
        print("\n".join(render_scenes(json.load(fh), sys.argv[2])))
