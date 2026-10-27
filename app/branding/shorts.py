"""Motor "shorts" Millón X: vídeo vertical con ritmo de creador.

Uso::

    python -m app.branding.shorts tools/millonx_ant_v2.json -o storage/millonx_ant_v2.mp4

Qué hace (ver README-millonx.md para el porqué de cada técnica):

1. Voz: Edge TTS (``es-ES-AlvaroNeural``) de todo el guion literal en una sola
   llamada, con tiempos por palabra (``WordBoundary``). Después se recortan los
   silencios largos entre frases (estilo jump-cut de audio) y se reajustan los
   tiempos. Si el resultado pasa de ``--max-duration`` se acelera y se repite.
2. Imagen: cada fotograma se dibuja con Pillow a 1080x1920 y 30 fps y se manda
   por tubería a ffmpeg (libx264). Por escena: fondo de marca (o B-roll de la
   carpeta local resource/broll/millonx, archivo o Pexels), frases que entran sincronizadas con la palabra que las dice,
   contadores que cuentan hasta la cifra, cámara siempre en movimiento
   (Ken Burns + punch-ins en cada golpe), whip-pan en los cortes, gancho con
   slam + flash + temblor en los primeros 0,5 s y final que enlaza con el inicio.
3. Capa fija: barra de progreso naranja, antetítulo, firma MILLÓN X y
   subtítulos karaoke palabra a palabra (palabra activa en naranja #F28C38 con
   pop) más emojis por palabra clave.
4. Audio: voz con EQ de presencia + compresión, efectos sintetizados
   (:mod:`app.branding.sfx`), música con ducking por sidechain bajo la voz y
   normalización a -14 LUFS.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.branding import sfx
from app.branding.charts import Chart, source_label
from app.branding.millonx import (ACCENTS, BG, BODY_FONT, GREY, HANDLE, HEADLINE_FONT, NAVY,
                                  ORANGE, WHITE, font_path)

W, H = 1080, 1920
FPS = 30
DEFAULT_MUSIC = "resource/songs/millonx_pulse.mp3"   # pista propia CC0 (app/branding/music.py)
DEFAULT_BROLL_DIR = "resource/broll/millonx"         # B-roll propio (generado con IA, ver LICENSES.md)
VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv")
SR = sfx.SR
MAX_W = 940
CAPTION_Y = 1470          # centro de los subtítulos (zona libre entre tarjeta y firma)
CAPTION_SIZE = 96
DARK = (8, 10, 16)
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# Emoji por palabra clave (minúsculas, sin tildes no hace falta: se compara tal cual)
EMOJI = {
    "perdido": "💸", "burbuja": "🫧", "calma": "🧘", "contable": "🧾", "real": "🔍",
    "facturado": "📈", "catorce": "🔥", "spacex": "🚀", "muerta": "💀", "mundo": "🌍",
    "nasdaq": "🔔", "caer": "📉", "leo": "👇",
}


# --------------------------------------------------------------------------- utilidades
def ease_out_cubic(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=2.2):
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def impulse(t, t0, decay):
    """1 en t0 y cae exponencialmente; 0 antes de t0."""
    return 0.0 if t < t0 else math.exp(-(t - t0) / decay)


_FONTS: dict = {}


def headline(size):
    key = ("h", size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(font_path(HEADLINE_FONT), size)
    return _FONTS[key]


def body(size):
    key = ("b", size)
    if key not in _FONTS:
        f = ImageFont.truetype(font_path(BODY_FONT), size)
        try:
            f.set_variation_by_name("ExtraBold")
        except Exception:
            pass
        _FONTS[key] = f
    return _FONTS[key]


def fit_headline(text, maxsize, max_w=MAX_W):
    s = maxsize
    while s > 30 and headline(s).getlength(text) > max_w:
        s -= 4
    return headline(s)


def color(c):
    return ACCENTS[c] if isinstance(c, str) else tuple(c)


def fmt_es(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


NUM_RE = re.compile(r"^(.*?)(\d{1,3}(?:\.\d{3})+|\d+)(.*)$")


# --------------------------------------------------------------------------- escenas
@dataclass
class Line:
    text: str
    size: int = 140
    color: str = "white"
    gap: int = 40
    cue: str | None = None
    count: dict | bool | None = None
    t_in: float = 0.0
    font: object = None
    y: int = 0
    h: int = 0


@dataclass
class Scene:
    say: str
    lines: list
    accent: str = "orange"
    kicker: str = ""
    punch: list = field(default_factory=list)
    hook: bool = False
    broll: str | None = None        # búsqueda de Pexels
    broll_file: str | None = None   # vídeo local (ruta o nombre dentro de --broll-dir)
    broll_dim: float = 0.55         # 0..1: cuánto tinte marino lleva el B-roll (legibilidad)
    chart: dict | None = None       # gráfica animada (app/branding/charts.py)
    source: str | None = None       # "Fuente: ..." pequeño en pantalla
    start: float = 0.0
    end: float = 0.0
    words: list = field(default_factory=list)
    punch_times: list = field(default_factory=list)


def _line(raw) -> Line:
    if isinstance(raw, (list, tuple)):
        text, size, col, gap = (list(raw) + [140, "white", 40])[:4]
        return Line(text=text, size=size, color=col, gap=gap)
    return Line(text=raw["text"], size=raw.get("size", 140), color=raw.get("color", "white"),
                gap=raw.get("gap", 40), cue=raw.get("cue"), count=raw.get("count"))


def load_scenes(path) -> list[Scene]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    scenes = data["scenes"] if isinstance(data, dict) else data
    out = []
    for s in scenes:
        if "say" not in s:
            raise ValueError("cada escena necesita 'say' (su trozo literal del guion)")
        out.append(Scene(say=s["say"].strip(), lines=[_line(l) for l in s["lines"]],
                         accent=s.get("accent", "orange"), kicker=s.get("kicker", ""),
                         punch=s.get("punch", []), hook=bool(s.get("hook")),
                         broll=s.get("broll"), broll_file=s.get("broll_file"),
                         broll_dim=float(s.get("broll_dim", 0.55)), chart=s.get("chart"),
                         source=s.get("source")))
    return out


# --------------------------------------------------------------------------- voz
@dataclass
class Word:
    text: str        # tal cual la devuelve Edge (puede ser "80.700 millones")
    shown: str       # con la puntuación del guion (¿?¡!)
    start: float
    end: float
    scene: int = 0
    brk: bool = False   # fin de frase/cláusula en el guion


def tts(text, voice, rate, pitch, volume, mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume,
                                boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as fh:
        for ch in comm.stream_sync():
            if ch["type"] == "audio":
                fh.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7
                words.append((st, st + ch["duration"] / 1e7, ch["text"]))
    return words


def decode(path, sr=SR) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1",
                          "-ar", str(sr), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def align_words(script, raw_words, scenes):
    """Asocia cada palabra de Edge a su posición en el guion y a su escena."""
    bounds, pos = [], 0
    for sc in scenes:
        bounds.append((pos, pos + len(sc.say)))
        pos += len(sc.say) + 1
    words, cur = [], 0
    for st, en, txt in raw_words:
        i = script.find(txt, cur)
        if i < 0:
            i = cur
            j = cur + len(txt)
        else:
            j = i + len(txt)
        a, b = i, j
        while a > 0 and script[a - 1] in "¿¡«\"":
            a -= 1
        while b < len(script) and script[b] in "?!»\"":
            b += 1
        nxt = script[j:j + 2]
        brk = bool(re.match(r"[.,:;?!]", nxt))
        scene = next((k for k, (s0, s1) in enumerate(bounds) if s0 <= i < s1 + 1), len(scenes) - 1)
        words.append(Word(text=txt, shown=script[a:b], start=st, end=en, scene=scene, brk=brk))
        cur = j
    return words


def tighten(audio, words, max_gap=0.2, scene_gap=0.3, lead=0.03, tail=0.5, tail_pad=0.05):
    """Jump-cut de audio: acorta los silencios largos y recoloca las palabras."""
    keep = []   # intervalos [a, b) en el audio original
    a = max(0.0, words[0].start - lead)
    for w, nx in zip(words, words[1:]):
        end = w.end + tail_pad
        limit = scene_gap if nx.scene != w.scene else max_gap
        if nx.start - end > limit:
            keep.append((a, end + limit / 2))
            a = nx.start - limit / 2
    keep.append((a, min(len(audio) / SR, words[-1].end + tail)))

    def remap(t):
        acc = 0.0
        for k0, k1 in keep:
            if t < k0:
                return acc
            if t <= k1:
                return acc + (t - k0)
            acc += k1 - k0
        return acc

    fade = int(0.006 * SR)
    pieces = []
    for k0, k1 in keep:
        seg = audio[int(k0 * SR):int(k1 * SR)].copy()
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            seg[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        pieces.append(seg)
    out = np.concatenate(pieces)
    for w in words:
        w.start, w.end = remap(w.start), remap(w.end)
    return out


# --------------------------------------------------------------------------- dibujo
def text_sprite(text, font, fill, stroke=0, shadow=6):
    bb = font.getbbox(text, stroke_width=stroke)
    pad = 20 + shadow
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    org = (pad - bb[0], pad - bb[1])
    if shadow:
        d.text((org[0] + shadow * 0.8, org[1] + shadow), text, font=font, fill=(0, 0, 0, 170),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    d.text(org, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=DARK)
    return im, pad


def scene_background(accent, seed=0):
    """Fondo de marca 12 % más grande que el lienzo para poder moverlo."""
    bw, bh = int(W * 1.12), int(H * 1.12)
    im = Image.new("RGB", (bw, bh), BG)
    lay = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    ox, oy = rng.integers(-120, 120, 2)
    d.ellipse([-300 + ox, -200 + oy, 950 + ox, 900 + oy], fill=accent + (80,))
    d.ellipse([450 - ox, 1150 - oy, 1500 - ox, 2300 - oy], fill=accent + (45,))
    lay = lay.filter(ImageFilter.GaussianBlur(170))
    im.paste(lay, (0, 0), lay)
    # rejilla sutil tipo "terminal de bolsa" para dar textura
    g = ImageDraw.Draw(im)
    for x in range(0, bw, 90):
        g.line([(x, 0), (x, bh)], fill=(255, 255, 255), width=1)
    for y in range(0, bh, 90):
        g.line([(0, y), (bw, y)], fill=(255, 255, 255), width=1)
    base = Image.new("RGB", (bw, bh), BG)
    base.paste(lay, (0, 0), lay)
    im = Image.blend(base, im, 0.06)   # rejilla al 6 %
    vign = Image.radial_gradient("L").resize((bw, bh)).point(lambda v: int(v * 0.75))
    im = Image.composite(Image.new("RGB", (bw, bh), (0, 0, 0)), im, vign)
    return im


class BrollReader:
    """Lee un vídeo (en bucle) ya recortado a 9:16 1080x1920 con tinte de marca."""

    def __init__(self, path, duration, dim=0.55):
        self.dim = dim
        vf = (f"scale={int(W*1.12)}:{int(H*1.12)}:force_original_aspect_ratio=increase,"
              f"crop={int(W*1.12)}:{int(H*1.12)},fps={FPS},eq=brightness=-0.12:saturation=0.8")
        self.size = (int(W * 1.12), int(H * 1.12))
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", path,
                                      "-t", f"{duration + 1:.2f}", "-vf", vf, "-f", "rawvideo",
                                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = None
        self.tint = Image.new("RGB", self.size, BG)

    def frame(self):
        n = self.size[0] * self.size[1] * 3
        buf = self.proc.stdout.read(n)
        if len(buf) == n:
            im = Image.frombuffer("RGB", self.size, buf, "raw", "RGB", 0, 1)
            self.last = Image.blend(im, self.tint, self.dim)
        return self.last

    def close(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def find_local_broll(query=None, name=None, folder=DEFAULT_BROLL_DIR):
    """B-roll sin API: busca en ``folder`` (por defecto resource/broll/millonx).

    - ``name``: ruta existente o nombre de archivo (con o sin extensión) dentro de la carpeta.
    - ``query``: términos; gana el archivo cuyas etiquetas (``broll.json`` de la carpeta,
      ``{"archivo.mp4": {"tags": [...]}}``) o nombre compartan más palabras con la búsqueda.
    """
    if name:
        for cand in (name, os.path.join(folder, name),
                     *(os.path.join(folder, name + e) for e in VIDEO_EXT)):
            if os.path.isfile(cand):
                return cand
    if not query or not os.path.isdir(folder):
        return None
    meta = {}
    mpath = os.path.join(folder, "broll.json")
    if os.path.exists(mpath):
        with open(mpath, encoding="utf-8") as fh:
            meta = json.load(fh)
    q = set(re.findall(r"\w+", query.lower()))
    best, score = None, 0
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(VIDEO_EXT):
            continue
        tags = set(re.findall(r"\w+", os.path.splitext(fn)[0].lower()))
        for tg in (meta.get(fn) or {}).get("tags", []):
            tags |= set(re.findall(r"\w+", tg.lower()))
        sc = len(q & tags)
        if sc > score:
            best, score = os.path.join(folder, fn), sc
    return best


def fetch_pexels(query, min_dur):
    """B-roll vertical de Pexels si hay ``pexels_api_keys`` en config.toml; si no, None."""
    try:
        from app.config import config
        if not config.app.get("pexels_api_keys"):
            return None
        from app.models.schema import VideoAspect
        from app.services import material
        items = material.search_videos_pexels(query, int(math.ceil(min_dur)), VideoAspect.portrait)
        for it in items:
            p = material.save_video(it.url)
            if p and os.path.exists(p):
                return p
    except Exception as e:  # B-roll es opcional: nunca rompe el render
        print(f"[shorts] B-roll de Pexels no disponible para {query!r}: {e}", file=sys.stderr)
    return None


# --------------------------------------------------------------------------- subtítulos
@dataclass
class Group:
    words: list
    start: float
    end: float
    emoji: str | None = None


def build_groups(words, max_words=3, max_chars=16):
    groups, cur = [], []

    def n_words(w):
        return len(w.text.split())

    for w in words:
        cur_chars = sum(len(x.shown) + 1 for x in cur)
        cur_n = sum(n_words(x) for x in cur)
        if cur and (cur_n + n_words(w) > max_words or cur_chars + len(w.shown) > max_chars
                    or cur[-1].brk or cur[-1].scene != w.scene):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1][0].start if i + 1 < len(groups) else g[-1].end + 0.6
        end = nxt if nxt - g[-1].end < 0.5 else g[-1].end + 0.25
        emo = None
        for w in g:
            key = re.sub(r"[^\wáéíóúñ]", "", w.text.lower().split()[-1])
            if key in EMOJI:
                emo = EMOJI[key]
        out.append(Group(words=g, start=g[0].start, end=end, emoji=emo))
    return out


class CaptionRenderer:
    def __init__(self):
        self.cache = {}
        self.emoji_cache = {}
        try:
            self.emoji_font = ImageFont.truetype(EMOJI_FONT, 109)
        except Exception:
            self.emoji_font = None

    def _layout(self, words, size):
        f = headline(size)
        space = f.getlength(" ")
        toks = [w.shown.upper().rstrip(".,:;") for w in words]
        widths = [f.getlength(t) for t in toks]
        lines, cur, cw = [], [], 0
        for i, wdt in enumerate(widths):
            if cur and cw + space + wdt > MAX_W:
                lines.append(cur)
                cur, cw = [], 0
            cw = cw + (space if cur else 0) + wdt
            cur.append(i)
        lines.append(cur)
        return f, toks, widths, space, lines

    def render(self, group: Group, active: int, pop: float):
        key = (id(group), active, round(pop, 2))
        if key in self.cache:
            return self.cache[key]
        size = CAPTION_SIZE
        f, toks, widths, space, lines = self._layout(group.words, size)
        while len(lines) > 2 and size > 60:
            size -= 8
            f, toks, widths, space, lines = self._layout(group.words, size)
        lh = int(size * 1.12)
        im = Image.new("RGBA", (W, lh * len(lines) + 80), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        act_font = headline(int(size * (1 + 0.18 * pop)))
        for li, idxs in enumerate(lines):
            # anchos reales (la palabra activa crece): así nunca se pisa con la vecina
            fonts = {i: (act_font if i == active else f) for i in idxs}
            real = {i: fonts[i].getlength(toks[i]) for i in idxs}
            total = sum(real.values()) + space * (len(idxs) - 1)
            x = (W - total) / 2
            cy = 40 + li * lh + lh / 2
            for i in idxs:
                ff = fonts[i]
                col = ORANGE if i == active else WHITE
                wx = x + real[i] / 2
                d.text((wx + 5, cy + 7), toks[i], font=ff, fill=(0, 0, 0, 190), anchor="mm",
                       stroke_width=9, stroke_fill=(0, 0, 0, 190))
                d.text((wx, cy), toks[i], font=ff, fill=col, anchor="mm",
                       stroke_width=9, stroke_fill=DARK)
                x += real[i] + space
        self.cache[key] = im
        return im

    def emoji(self, ch, scale):
        if not self.emoji_font or scale <= 0.02:
            return None
        key = (ch, round(scale, 2))
        if key in self.emoji_cache:
            return self.emoji_cache[key]
        base = self.emoji_cache.get((ch, "base"))
        if base is None:
            base = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(base).text((80, 80), ch, font=self.emoji_font, embedded_color=True,
                                      anchor="mm")
            if base.getbbox() is None:   # glifo no disponible en la fuente
                self.emoji_font_missing = True
                self.emoji_cache[key] = None
                return None
            self.emoji_cache[(ch, "base")] = base
        s = max(1, int(140 * scale))
        im = base.resize((s, s), Image.LANCZOS)
        self.emoji_cache[key] = im
        return im


# --------------------------------------------------------------------------- render
class Renderer:
    def __init__(self, scenes, words, duration, loop=True, broll_dir=DEFAULT_BROLL_DIR):
        self.scenes, self.words, self.T, self.loop = scenes, words, duration, loop
        self.groups = build_groups(words)
        self.caps = CaptionRenderer()
        self.bgs = [scene_background(color(s.accent), seed=i) for i, s in enumerate(scenes)]
        self.broll = {}
        for i, s in enumerate(scenes):
            # orden: archivo indicado -> carpeta local (sin API) -> Pexels si hay clave
            path = find_local_broll(name=s.broll_file, folder=broll_dir) if s.broll_file else None
            if not path and s.broll:
                path = find_local_broll(query=s.broll, folder=broll_dir)
            if not path and s.broll:
                path = fetch_pexels(s.broll, s.end - s.start)
            if path:
                print(f"[shorts] B-roll escena {i + 1}: {path}")
                self.broll[i] = BrollReader(path, s.end - s.start, dim=s.broll_dim)
        self.charts = {}
        for i, s in enumerate(scenes):
            if s.chart:
                ch = Chart(dict(s.chart), color, headline, body, W)
                ch.resolve(lambda cue, s=s: self._cue_time(s, cue), s.start)
                self.charts[i] = ch
        self.sources = {}
        self.sprites = {}
        self._layout()
        self.overlay_static = self._signature()
        self.kickers = {}
        self.events = []      # (t, tipo, extra) para la pista de efectos

    @staticmethod
    def _cue_time(sc, cue):
        w = next((w for w in sc.words if cue.lower() in w.text.lower()), None)
        return max(sc.start, w.start - 0.06) if w else None

    # -- maquetación de las frases de cada tarjeta
    def _layout(self):
        for sc in self.scenes:
            for ln in sc.lines:
                ln.font = fit_headline(ln.text, ln.size)
                bb = ln.font.getbbox(ln.text)
                ln.h = bb[3] - bb[1]
            total = sum(l.h for l in sc.lines) + sum(l.gap for l in sc.lines[:-1])
            if sc.chart:   # las frases van encima de la gráfica
                bottom = int(sc.chart.get("y", 860)) - 40
                y = max(230, (230 + bottom - total) // 2)
            else:
                y = max(260, (1300 - total) // 2 + 60)
            for ln in sc.lines:
                ln.y = y
                y += ln.h + ln.gap
            # momento de entrada de cada frase: su "cue" o escalonado
            n = len(sc.lines)
            for k, ln in enumerate(sc.lines):
                t = None
                if ln.cue:
                    w = next((w for w in sc.words if ln.cue.lower() in w.text.lower()), None)
                    t = w.start - 0.06 if w else None
                if t is None:
                    t = sc.start + (0 if k == 0 else k * min(0.45, (sc.end - sc.start) * 0.5 / n))
                ln.t_in = max(sc.start, t)
            sc.punch_times = [w.start for w in sc.words
                              if any(p.lower() in w.text.lower() for p in sc.punch)]

    def _signature(self):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        f = body(32)
        d.rounded_rectangle([50, H - 130, W - 50, H - 60], radius=35, fill=NAVY + (235,))
        x, y = 85, H - 115
        d.text((x, y), "MILLÓN", font=f, fill=WHITE)
        x += f.getlength("MILLÓN ")
        d.text((x, y), "X", font=f, fill=ORANGE)
        hf = body(30)
        d.text((W - 85 - hf.getlength(HANDLE), y + 2), HANDLE, font=hf, fill=GREY)
        return im

    def _kicker(self, i):
        if i not in self.kickers:
            sc = self.scenes[i]
            im = Image.new("RGBA", (W, 80), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            f = body(34)
            if sc.kicker:
                tw = f.getlength(sc.kicker.upper())
                d.rounded_rectangle([60, 10, 60 + tw + 44, 70], radius=30,
                                    fill=color(sc.accent) + (60,))
                d.text((82, 20), sc.kicker.upper(), font=f, fill=WHITE)
            self.kickers[i] = im
        return self.kickers[i]

    def _line_text(self, ln, t):
        if not ln.count:
            return ln.text
        m = NUM_RE.match(ln.text)
        if not m:
            return ln.text
        pre, num, post = m.groups()
        target = float(num.replace(".", ""))
        start = float(ln.count.get("from", 0)) if isinstance(ln.count, dict) else 0.0
        dur = float(ln.count.get("dur", 0.75)) if isinstance(ln.count, dict) else 0.75
        v = start + (target - start) * ease_out_cubic((t - ln.t_in) / dur)
        return pre + fmt_es(v) + post

    def _sprite(self, ln, text):
        key = (id(ln), text)
        if key not in self.sprites:
            self.sprites[key] = text_sprite(text, ln.font, color(ln.color), shadow=7)
        return self.sprites[key]

    def scene_at(self, t):
        for i, s in enumerate(self.scenes):
            if t < s.end:
                return i
        return len(self.scenes) - 1

    # -- un fotograma
    def frame(self, t, clean=False):
        i = self.scene_at(t)
        sc = self.scenes[i]
        ts = sc.start if i > 0 else 0.0
        if i in self.broll:
            bg = self.broll[i].frame() or self.bgs[i]
        else:
            bg = self.bgs[i]
        canvas = bg.copy()
        ox = (canvas.width - W) // 2
        oy = (canvas.height - H) // 2
        for ln in sc.lines:
            if t < ln.t_in:
                continue
            txt = self._line_text(ln, t)
            spr, pad = self._sprite(ln, txt)
            a = (t - ln.t_in) / 0.22
            s = 0.55 + 0.45 * ease_out_back(a) if a < 1 else 1.0
            if sc.hook and ln is sc.lines[0]:
                s = 1.0 + 0.28 * (1 - ease_out_cubic((t - ln.t_in) / 0.16))   # slam
            if sc.hook and ln is sc.lines[0]:
                s = min(s, (W - 160) / spr.width)         # el slam nunca se sale del lienzo
            if s != 1.0:
                spr = spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))),
                                 Image.BILINEAR)
            if a < 0.35 and not (sc.hook and ln is sc.lines[0]):
                alpha = spr.getchannel("A").point(lambda v, k=a / 0.35: int(v * k))
                spr = spr.copy()
                spr.putalpha(alpha)
            cx = ox + W // 2
            cy = oy + ln.y + ln.h // 2
            canvas.paste(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)), spr)

        if i in self.charts:
            canvas = canvas.convert("RGBA")
            self.charts[i].draw(canvas, ox, oy, t, ts)
            canvas = canvas.convert("RGB")

        # cámara: Ken Burns + punch-ins
        p = (t - ts) / max(0.1, sc.end - ts)
        z = 1.0 + 0.05 * p
        z += 0.10 * impulse(t, ts, 0.10) if i > 0 else 0
        for ln in sc.lines[1:]:
            z += 0.035 * impulse(t, ln.t_in, 0.14)
        for pt in sc.punch_times:
            z += 0.06 * impulse(t, pt, 0.16)
        if sc.hook:
            z += 0.12 * impulse(t, 0.0, 0.09)
        sx = sy = 0.0
        if sc.hook:
            amp = 22 * impulse(t, 1 / FPS, 0.14)
            sx, sy = amp * math.sin(t * 97), amp * math.cos(t * 71)
        if i > 0:
            amp = 7 * impulse(t, ts, 0.08)
            sx += amp * math.sin(t * 89)
        drift = 18 * math.sin(t * 0.7 + i)
        cw, ch = W / z, H / z
        cx = canvas.width / 2 + drift + sx
        cy = canvas.height / 2 + sy
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        img = canvas.resize((W, H), Image.BILINEAR, box=box)

        # whip-pan al entrar en escena (desenfoque direccional 3 fotogramas)
        if i > 0 and not clean and t - ts < 3 / FPS:
            arr = np.asarray(img).astype(np.float32)
            k = 1 - (t - ts) * FPS / 3
            dx = int(60 * k) * (1 if i % 2 else -1)
            acc = arr.copy()
            for j in range(1, 6):
                acc += np.roll(arr, dx * j // 5, axis=1)
            img = Image.fromarray((acc / 6).astype(np.uint8))

        # capa fija: antetítulo, firma, barra de progreso, subtítulos, emoji
        img = img.convert("RGBA")
        img.alpha_composite(self._kicker(i), (0, 70))
        img.alpha_composite(self.overlay_static)
        if sc.source and not clean:
            if sc.source not in self.sources:
                self.sources[sc.source] = source_label(sc.source, body, W)
            img.alpha_composite(self.sources[sc.source], (0, H - 200))
        d = ImageDraw.Draw(img)
        prog = min(1.0, t / self.T)
        d.rectangle([0, 0, W, 12], fill=NAVY + (255,))
        d.rectangle([0, 0, int(W * prog), 12], fill=ORANGE + (255,))
        d.ellipse([int(W * prog) - 9, -3, int(W * prog) + 9, 15], fill=WHITE + (255,))

        g = None if clean else next((g for g in self.groups if g.start - 0.03 <= t < g.end), None)
        if g is not None:
            act, act_t = -1, g.start
            for k, w in enumerate(g.words):
                if t >= w.start - 0.03:
                    act, act_t = k, w.start
            pop = impulse(t, act_t, 0.07) if act >= 0 else 0.0
            cap = self.caps.render(g, act, round(pop * 10) / 10)
            ent = ease_out_cubic((t - g.start + 0.03) / 0.08)
            y = int(CAPTION_Y - cap.height / 2 + 26 * (1 - ent))
            img.alpha_composite(cap, (0, y))
            if g.emoji:
                es = ease_out_back((t - g.start) / 0.2) if t - g.start < 0.2 else 1.0
                em = self.caps.emoji(g.emoji, max(0.0, es))
                if em is not None:
                    bob = 6 * math.sin((t - g.start) * 9)
                    img.alpha_composite(em, (W // 2 - em.width // 2,
                                             int(y - em.height + 20 + bob)))

        # flash en el gancho y en cada corte
        # fotograma 0 limpio (sirve de miniatura); el flash pega en el 1.º-3.º fotograma
        fl = 0.0 if clean else (0.42 * impulse(t, 1 / FPS, 0.05) if sc.hook else 0.0)
        if i > 0 and not clean:
            fl = max(fl, 0.16 * impulse(t, ts, 0.05))
        out = img.convert("RGB")
        if fl > 0.01:
            out = Image.blend(out, Image.new("RGB", (W, H), WHITE), min(fl, 0.9))
        return out


# --------------------------------------------------------------------------- audio
def build_sfx(r: Renderer, T):
    tr = sfx.Track(T)
    boom, wh, wh2 = sfx.impact(), sfx.whoosh(seed=2), sfx.whoosh(seed=5)
    tr.place(boom, 0.0, gain_db=-2)
    for i, sc in enumerate(r.scenes[1:], 1):
        tr.place(wh if i % 2 else wh2, sc.start, gain_db=-9, hit=0.27)
    pops = [520, 590, 660, 740]
    for sc in r.scenes:
        for k, ln in enumerate(sc.lines):
            if (sc.hook and k == 0) or abs(ln.t_in - sc.start) < 0.05:
                continue
            tr.place(sfx.pop(pops[k % len(pops)]), ln.t_in, gain_db=-14)
            if ln.count:
                dur = ln.count.get("dur", 0.75) if isinstance(ln.count, dict) else 0.75
                n = int(dur / 0.06)
                for j in range(n):
                    tr.place(sfx.tick(1800 + 60 * j), ln.t_in + j * 0.06,
                             gain_db=-22 - 6 * (j / n))
        for pt in sc.punch_times:
            tr.place(sfx.pop(420, 0.16), pt, gain_db=-12)
    for ch in r.charts.values():
        for t0, kind in ch.cue_times():
            if kind == "badge":
                tr.place(sfx.pop(880, 0.18), t0, gain_db=-11)
            else:
                for j in range(8):
                    tr.place(sfx.tick(1500 + 90 * j), t0 + j * 0.07, gain_db=-24 - 2 * j)
    last = r.scenes[-1]
    tr.place(sfx.riser(0.7), last.start, gain_db=-16, hit=0.7)
    return tr.render(T)


def mix(voice_wav, sfx_wav, music, out_wav, T, music_db=-12.0, music_start=0.0):
    fc = (
        "[0:a]highpass=f=75,equalizer=f=220:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3.5,"
        "equalizer=f=9000:t=q:w=1:g=1.5,acompressor=threshold=-22dB:ratio=3.5:attack=4:"
        "release=70:makeup=3,asplit=2[v][key];"
    )
    inputs = ["-i", voice_wav, "-i", sfx_wav]
    if music and os.path.exists(music):
        inputs += (["-ss", f"{music_start}"] if music_start else []) + ["-i", music]
        fc += (f"[2:a]aformat=channel_layouts=mono,aresample={SR},atrim=duration={T:.3f},"
               f"volume={music_db}dB,afade=t=in:d=0.15,afade=t=out:st={max(0, T-0.8):.3f}:d=0.8[m];"
               "[m][key]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=400:"
               "makeup=1[md];[1:a]volume=-1dB[s];"
               "[v][md][s]amix=inputs=3:normalize=0:duration=first[mx];")
    else:
        fc += "[key]anullsink;[v][1:a]amix=inputs=2:normalize=0:duration=first[mx];"
    fc += "[mx]loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[out]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
                    "-map", "[out]", "-ac", "2", "-ar", "48000", out_wav], check=True)


# --------------------------------------------------------------------------- orquestación
def build(scenes_path, out, voice="es-ES-AlvaroNeural", rate=15, pitch="+3Hz", volume="+0%",
          music=DEFAULT_MUSIC, max_duration=30.0, keep_dir=None,
          music_db=-12.0, music_start=0.0, broll_dir=DEFAULT_BROLL_DIR):
    scenes = load_scenes(scenes_path)
    script = " ".join(s.say for s in scenes)
    work = keep_dir or tempfile.mkdtemp(prefix="millonx_shorts_")
    os.makedirs(work, exist_ok=True)
    for attempt in range(5):
        mp3 = os.path.join(work, "voice_raw.mp3")
        raw_words = tts(script, voice, f"+{rate}%", pitch, volume, mp3)
        words = align_words(script, raw_words, scenes)
        audio = tighten(decode(mp3), words)
        T = len(audio) / SR
        print(f"[shorts] voz {voice} rate=+{rate}% pitch={pitch}: {T:.2f}s")
        if T <= max_duration - 0.3:
            break
        rate += 5
    voice_wav = os.path.join(work, "voice.wav")
    write_wav(voice_wav, audio)
    # escenas: del inicio de su primera palabra al de la siguiente escena
    for k, sc in enumerate(scenes):
        sc.words = [w for w in words if w.scene == k]
        sc.start = 0.0 if k == 0 else sc.words[0].start - 0.12
    for k, sc in enumerate(scenes):
        sc.end = scenes[k + 1].start if k + 1 < len(scenes) else T
    r = Renderer(scenes, words, T, broll_dir=broll_dir)
    sfx_wav = os.path.join(work, "sfx.wav")
    write_wav(sfx_wav, build_sfx(r, T))
    mix_wav = os.path.join(work, "mix.wav")
    if music and not os.path.exists(music) and os.path.abspath(music) == os.path.abspath(DEFAULT_MUSIC):
        from app.branding import music as music_gen       # se regenera de forma determinista
        music_gen.write(music)
    mix(voice_wav, sfx_wav, music, mix_wav, T, music_db=music_db, music_start=music_start)

    n = int(math.ceil(T * FPS))
    loop_frames = 5
    first = r.frame(0.3, clean=True) if r.loop else None
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", mix_wav,
                            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac",
                            "-b:a", "192k", "-movflags", "+faststart", "-shortest", out],
                           stdin=subprocess.PIPE)
    for f in range(n):
        t = f / FPS
        im = r.frame(t)
        if first is not None and f >= n - loop_frames:      # final que enlaza con el inicio
            k = (f - (n - loop_frames) + 1) / loop_frames
            im = Image.blend(im, first, ease_out_cubic(k))
            arr = np.asarray(im).astype(np.float32)
            dx = int(70 * math.sin(math.pi * k))
            acc = arr.copy()
            for j in range(1, 6):
                acc += np.roll(arr, dx * j // 5, axis=1)
            im = Image.fromarray((acc / 6).astype(np.uint8))
        enc.stdin.write(im.tobytes())
        if f % 60 == 0:
            print(f"[shorts] {f}/{n}", flush=True)
    enc.stdin.close()
    enc.wait()
    for b in r.broll.values():
        b.close()
    with open(os.path.join(work, "timeline.json"), "w", encoding="utf-8") as fh:
        json.dump({"duration": T, "rate": rate, "voice": voice, "pitch": pitch,
                   "scenes": [{"start": s.start, "end": s.end, "say": s.say,
                               "lines": [(l.text, round(l.t_in, 2)) for l in s.lines]}
                              for s in scenes],
                   "words": [(w.shown, round(w.start, 3), round(w.end, 3)) for w in words]},
                  fh, ensure_ascii=False, indent=1)
    if enc.returncode != 0:
        raise RuntimeError("ffmpeg falló al codificar el vídeo")
    print(f"[shorts] listo: {out} ({T:.2f}s) · trabajo en {work}")
    return out, T


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vídeo vertical Millón X con ritmo de creador")
    ap.add_argument("scenes")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--voice", default="es-ES-AlvaroNeural")
    ap.add_argument("--rate", type=int, default=15, help="velocidad Edge TTS en %% (+15 = 1,15x)")
    ap.add_argument("--pitch", default="+3Hz")
    ap.add_argument("--music-start", type=float, default=0.0,
                    help="segundo de la pista en el que empieza la música (0 para la pista propia)")
    ap.add_argument("--music", default=DEFAULT_MUSIC,
                    help="'' para sin música")
    ap.add_argument("--music-db", type=float, default=-12.0,
                    help="ganancia de la música antes del ducking; con la pista propia (-14 LUFS) -12 dB deja la música ~17 dB bajo la voz, igual que en la v2")
    ap.add_argument("--max-duration", type=float, default=30.0)
    ap.add_argument("--broll-dir", default=DEFAULT_BROLL_DIR,
                    help="carpeta de B-roll local (sin API); ver resource/broll/millonx/broll.json")
    ap.add_argument("--keep", default=None, help="carpeta para dejar audio/timeline intermedios")
    a = ap.parse_args(argv)
    build(a.scenes, a.out, a.voice, a.rate, a.pitch, music=a.music,
          max_duration=a.max_duration, keep_dir=a.keep, music_db=a.music_db,
          music_start=a.music_start, broll_dir=a.broll_dir)


if __name__ == "__main__":
    main()
