"""Gráficas animadas Millón X (dibujadas por código, sin assets de terceros).

Se usan desde :mod:`app.branding.shorts` con el campo ``"chart"`` de una escena.
Cada barra entra sincronizada con una palabra de la voz (``cue``) y crece con
ease-out mientras su cifra cuenta hasta el valor real.

Tipos:

``hbars``  barras horizontales en un panel (p. ej. pérdida neta 80.700 vs apunte
           contable 72.400 vs pérdida operativa 693). Escala común = ``max``.
``vbars``  columnas (p. ej. ingresos 1.200 -> 16.300) con insignia opcional
           (``badge``: "x14") que salta en su ``cue``.

Solo se pintan las cifras que vienen en el JSON: el motor no inventa datos.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from app.branding.millonx import BG, GREY, NAVY, WHITE


def _ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _back(x, s=2.2):
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def fmt_es(n):
    return f"{int(round(n)):,}".replace(",", ".")


class Chart:
    """Gráfica de una escena. ``spec`` viene del JSON; ``color``, ``headline`` y
    ``body`` los inyecta el motor para no duplicar paleta ni fuentes."""

    GROW = 0.65   # segundos que tarda una barra en crecer

    def __init__(self, spec, color, headline, body, W=1080):
        self.spec, self.color, self.headline, self.body, self.W = spec, color, headline, body, W
        self.type = spec.get("type", "hbars")
        self.y = int(spec.get("y", 860))
        self.h = int(spec.get("h", 440))
        self.x0, self.x1 = 70, W - 70
        self.bars = spec["bars"]
        self.max = float(spec.get("max") or max(b["value"] for b in self.bars))
        self.badge = spec.get("badge")
        for b in self.bars:
            b.setdefault("t_in", 0.0)
        if self.badge:
            self.badge.setdefault("t_in", 0.0)
        self._panel = None

    # tiempos: el motor llama a resolve() con una función palabra -> segundo
    def resolve(self, cue_time, scene_start):
        for b in self.bars:
            t = cue_time(b.get("cue")) if b.get("cue") else None
            b["t_in"] = scene_start - 1.0 if b.get("instant") else (t if t is not None else scene_start)
        if self.badge:
            t = cue_time(self.badge.get("cue")) if self.badge.get("cue") else None
            self.badge["t_in"] = t if t is not None else scene_start + 0.5

    def cue_times(self):
        """(segundo, tipo) para la pista de efectos: barras que crecen y la insignia."""
        out = [(b["t_in"], "bar") for b in self.bars if not b.get("instant")]
        if self.badge:
            out.append((self.badge["t_in"], "badge"))
        return out

    def _panel_img(self):
        if self._panel is None:
            w, h = self.x1 - self.x0, self.h
            im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([30, 36, 30 + w, 36 + h], radius=34, fill=(0, 0, 0, 120))
            im = im.filter(ImageFilter.GaussianBlur(14))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([30, 30, 30 + w, 30 + h], radius=34, fill=NAVY + (215,),
                                outline=(255, 255, 255, 28), width=2)
            self._panel = im
        return self._panel

    def draw(self, canvas: Image.Image, ox, oy, t, scene_start):
        a = _ease((t - scene_start) / 0.25)
        if a <= 0:
            return
        panel = self._panel_img()
        if a < 1:
            panel = panel.copy()
            panel.putalpha(panel.getchannel("A").point(lambda v: int(v * a)))
        dy = int(40 * (1 - a))
        canvas.alpha_composite(panel, (ox + self.x0 - 30, oy + self.y - 30 + dy))
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        if self.type == "vbars":
            self._vbars(d, lay, ox, oy + dy, t)
        else:
            self._hbars(d, lay, ox, oy + dy, t)
        canvas.alpha_composite(lay)

    def _value(self, b, k):
        txt = b.get("fmt", "{v} M$")
        pre = b.get("prefix", "")
        v = b["value"] * k if b.get("count", True) else b["value"]
        return pre + txt.replace("{v}", fmt_es(v))

    def _hbars(self, d, lay, ox, oy, t):
        n = len(self.bars)
        pad = 44
        inner_w = self.x1 - self.x0 - 2 * pad
        row = (self.h - 2 * pad) / n
        lf, vf = self.body(34), self.headline(58)
        for k, b in enumerate(self.bars):
            if t < b["t_in"]:
                continue
            g = _ease((t - b["t_in"]) / self.GROW)
            x = ox + self.x0 + pad
            y = oy + self.y + pad + k * row
            col = self.color(b.get("color", "white"))
            al = int(255 * min(1, (t - b["t_in"]) / 0.15 + 0.0)) if not b.get("instant") else 255
            d.text((x, y), b["label"].upper(), font=lf, fill=GREY + (al,))
            d.text((x + inner_w, y - 14), self._value(b, g), font=vf, fill=col + (al,), anchor="ra")
            by = y + 62
            bh = max(26, min(54, row - 100))
            d.rounded_rectangle([x, by, x + inner_w, by + bh], radius=bh // 2, fill=BG + (230,))
            frac = b["value"] / self.max
            bw = max(bh * 0.5, inner_w * frac * g)
            d.rounded_rectangle([x, by, x + bw, by + bh], radius=bh // 2, fill=col + (255,))
            if frac < 0.03 and g > 0:   # barra diminuta: halo que late para que se vea
                r = bh * (1.0 + 0.35 * (0.5 + 0.5 * math.sin((t - b["t_in"]) * 9)))
                cx, cy = x + bw / 2, by + bh / 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (200,), width=5)
                note = b.get("note")
                if note:
                    d.text((x + bh * 1.6, by + bh / 2), note, font=self.body(30),
                           fill=col + (al,), anchor="lm")

    def _vbars(self, d, lay, ox, oy, t):
        n = len(self.bars)
        pad_t, pad_b = 110, 86
        span = self.x1 - self.x0
        colw = span / n
        bw = min(230, colw * 0.52)
        base = oy + self.y + self.h - pad_b
        top = oy + self.y + pad_t
        lf, vf = self.body(34), self.headline(62)
        d.line([(ox + self.x0 + 50, base), (ox + self.x1 - 50, base)], fill=GREY + (120,), width=3)
        tops = []
        for k, b in enumerate(self.bars):
            cx = ox + self.x0 + colw * (k + 0.5)
            d.text((cx, base + 20), b["label"].upper(), font=lf, fill=GREY + (255,), anchor="ma")
            if t < b["t_in"]:
                tops.append(None)
                continue
            g = _ease((t - b["t_in"]) / self.GROW)
            col = self.color(b.get("color", "white"))
            hgt = max(10, (base - top) * b["value"] / self.max * g)
            d.rounded_rectangle([cx - bw / 2, base - hgt, cx + bw / 2, base], radius=18,
                                fill=col + (255,))
            d.text((cx, base - hgt - 14), self._value(b, g), font=vf, fill=col + (255,),
                   anchor="mb")
            tops.append((cx, base - hgt))
        if self.badge and t >= self.badge["t_in"] and all(tops):
            s = _back((t - self.badge["t_in"]) / 0.3)
            col = self.color(self.badge.get("color", "orange"))
            (x0, y0), (x1, y1) = tops[0], tops[-1]
            # flecha de la primera a la última columna
            ax0, ay0 = x0 + bw / 2 + 20, y0 - 90
            ax1, ay1 = x1 - bw / 2 - 30, y1 + 70
            k = _ease((t - self.badge["t_in"]) / 0.35)
            ex, ey = ax0 + (ax1 - ax0) * k, ay0 + (ay1 - ay0) * k
            d.line([(ax0, ay0), (ex, ey)], fill=col + (255,), width=10)
            if k > 0.9:
                ang = math.atan2(ay1 - ay0, ax1 - ax0)
                for da in (2.6, -2.6):
                    d.line([(ex, ey), (ex + 34 * math.cos(ang + da), ey + 34 * math.sin(ang + da))],
                           fill=col + (255,), width=10)
            f = self.headline(max(10, int(110 * s)))
            bx, by = (ax0 + ax1) / 2 - 40, (ay0 + ay1) / 2 - 40
            tw = f.getlength(self.badge["text"])
            d.rounded_rectangle([bx - tw / 2 - 30, by - 75 * s, bx + tw / 2 + 30, by + 75 * s],
                                radius=int(40 * s), fill=col + (255,))
            d.text((bx, by), self.badge["text"], font=f, fill=BG + (255,), anchor="mm")


def source_label(text, body, W=1080):
    """Pastilla pequeña 'Fuente: ...' para la capa fija."""
    f = body(26)
    tw = f.getlength(text)
    im = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = (W - tw) / 2
    d.rounded_rectangle([x - 18, 4, x + tw + 18, 46], radius=21, fill=BG + (190,))
    d.text((x, 11), text, font=f, fill=GREY + (255,))
    return im
