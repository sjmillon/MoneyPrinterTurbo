"""Pista musical propia de Millón X, sintetizada con numpy («Pulso Millón X»).

Obra original generada íntegramente por este código: no usa muestras, loops ni
presets de terceros, así que no hay derechos ajenos ni riesgo de Content ID. Se
dedica al dominio público con CC0 1.0 (ver resource/songs/LICENSES.md).

Estilo: electrónica / lo-fi enérgica a 120 BPM en La menor (Am–F–C–G), 16
compases = 32 s (sin cortes: el vídeo dura ~29 s). Kick a negras con sidechain (bombeo), palmada en 2 y 4,
charles a corcheas con abierto a contratiempo, bajo sierra filtrado, pad
supersaw ancho, arpegio pluck a semicorcheas, saturación suave y polvo de
vinilo muy bajo. Deja hueco en medios (1–4 kHz) para la voz.

    python -m app.branding.music resource/songs/millonx_pulse.mp3
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import wave

import numpy as np

SR = 48000
BPM = 120
BEAT = 60.0 / BPM
BAR = 4 * BEAT
BARS = 16
BREAKDOWN_BARS: tuple[int, ...] = ()   # p. ej. (12,) para un respiro sin kick
TOTAL = BARS * BAR + 1.5          # cola para la reverb/release
RNG = np.random.default_rng(20261027)

# La menor: Am – F – C – G (raíces MIDI del bajo y acordes del pad)
PROG = [(45, [57, 60, 64, 69]), (41, [53, 57, 60, 65]),
        (48, [55, 60, 64, 67]), (43, [55, 59, 62, 67])]


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def t_(d: float) -> np.ndarray:
    return np.arange(int(SR * d)) / SR


def fft_filter(x: np.ndarray, lo: float = 0.0, hi: float = SR / 2, slope: float = 1.0) -> np.ndarray:
    """Paso banda suave por FFT (ganancia con caída tipo butterworth)."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.ones_like(f)
    if hi < SR / 2:
        g /= np.sqrt(1 + (f / hi) ** (4 * slope))
    if lo > 0:
        g /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (4 * slope))
    return np.fft.irfft(X * g, n)


def saw(freq: float, d: float, detune: float = 0.0, phase: float = 0.0) -> np.ndarray:
    t = t_(d)
    f = freq * 2 ** (detune / 1200)
    out = np.zeros_like(t)
    k = 1
    while k * f < 9000:
        out += np.sin(2 * np.pi * k * f * t + phase * k) / k
        k += 1
    return out * 0.6


def env_adsr(n: int, a=0.005, d=0.1, s=0.7, r=0.05) -> np.ndarray:
    e = np.full(n, s)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na, endpoint=False)
    e[na:na + nd] = np.linspace(1, s, len(e[na:na + nd]))
    if nr and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


class Bus:
    def __init__(self):
        self.L = np.zeros(int(SR * TOTAL))
        self.R = np.zeros(int(SR * TOTAL))

    def add(self, x, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        x = x[: max(0, len(self.L) - i)]
        gl, gr = gain * np.sqrt((1 - pan) / 2) * 1.414, gain * np.sqrt((1 + pan) / 2) * 1.414
        self.L[i:i + len(x)] += x * gl
        self.R[i:i + len(x)] += x * gr

    def add_st(self, l, r, t, gain=1.0):
        i = int(t * SR)
        n = min(len(l), len(self.L) - i)
        self.L[i:i + n] += l[:n] * gain
        self.R[i:i + n] += r[:n] * gain


# ------------------------------------------------------------------ instrumentos
def kick() -> np.ndarray:
    t = t_(0.45)
    f = 48 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7.5)
    click = fft_filter(RNG.standard_normal(len(t)), 1500, 6000) * np.exp(-t * 400) * 0.25
    return np.tanh(1.6 * (body + click)) * 0.9


def clap() -> np.ndarray:
    t = t_(0.35)
    n = RNG.standard_normal(len(t))
    e = np.zeros_like(t)
    for off in (0, 0.011, 0.022):           # tres «manos» rápidas
        tt = np.clip(t - off, 0, None)
        e += (t >= off) * np.exp(-tt * 140) * 0.7
    e += (t >= 0.03) * np.exp(-np.clip(t - 0.03, 0, None) * 16) * 0.5
    return fft_filter(n * e, 900, 5200) * 0.9


def hat(open_: bool = False) -> np.ndarray:
    d = 0.22 if open_ else 0.05
    t = t_(d)
    n = fft_filter(RNG.standard_normal(len(t)), 7000, 16000)
    return n * np.exp(-t * (14 if open_ else 90)) * 0.5


def bass(m: int, d: float) -> np.ndarray:
    x = saw(hz(m), d) + 0.6 * np.sin(2 * np.pi * hz(m - 12) * t_(d))
    x = fft_filter(x, 30, 420)
    return np.tanh(1.8 * x) * env_adsr(len(x), 0.004, 0.12, 0.75, 0.03) * 0.55


def pad(notes, d, cutoff) -> tuple[np.ndarray, np.ndarray]:
    L = np.zeros(int(SR * d))
    R = np.zeros_like(L)
    for m in notes:
        for det, side in ((-9, 0), (9, 1), (-3, 1), (4, 0)):
            v = saw(hz(m), d, det, RNG.uniform(0, 6.28))
            (L if side == 0 else R)[:] += v
    e = env_adsr(len(L), 0.25, 0.4, 0.8, 0.35)
    return fft_filter(L, 180, cutoff) * e * 0.06, fft_filter(R, 180, cutoff) * e * 0.06


def pluck(m: int, d: float = 0.22) -> np.ndarray:
    t = t_(d)
    f = hz(m)
    x = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * 2 * f * t) * 0.3
    x = fft_filter(x, 300, 3800)
    return x * np.exp(-t * 18) * 0.22


def riser(d: float) -> np.ndarray:
    t = t_(d)
    n = RNG.standard_normal(len(t))
    lo = fft_filter(n, 2000, 9000)
    return lo * (t / d) ** 2 * 0.18


# ------------------------------------------------------------------ arreglo
def render() -> tuple[np.ndarray, np.ndarray]:
    drums, music = Bus(), Bus()
    K, C, H, HO = kick(), clap(), hat(), hat(True)
    kick_times = []
    for bar in range(BARS):
        t0 = bar * BAR
        root, chord = PROG[bar % 4]
        breakdown = bar in BREAKDOWN_BARS
        intro = bar < 1
        # batería
        for b in range(4):
            if not breakdown:
                drums.add(K, t0 + b * BEAT, 1.0)
                kick_times.append(t0 + b * BEAT)
            if b in (1, 3) and not intro:
                drums.add(C, t0 + b * BEAT, 0.55, pan=0.05)
        if not intro:
            for e in range(8):
                swing = 0.018 if e % 2 else 0.0            # pizca de swing lo-fi
                if e % 2 and not breakdown:
                    drums.add(HO, t0 + e * BEAT / 2 + swing, 0.32, pan=0.25)
                else:
                    drums.add(H, t0 + e * BEAT / 2 + swing, 0.38 * RNG.uniform(0.75, 1), pan=-0.2)
        if bar == 15 or bar == 7:            # redoble de transición
            for s in range(4):
                drums.add(C, t0 + 3 * BEAT + s * BEAT / 4, 0.25 + 0.1 * s)
        # bajo (corcheas con salto de octava)
        if not breakdown:
            for e in range(8):
                m = root + (12 if e in (3, 7) else 0)
                music.add(bass(m, BEAT / 2 * 0.9), t0 + e * BEAT / 2, 1.0)
        # pad, se abre durante la intro
        cutoff = 900 if intro else (1400 if breakdown else 2400)
        l, r = pad(chord, BAR, cutoff)
        music.add_st(l, r, t0, 1.0)
        # arpegio a semicorcheas desde el compás 2
        if bar >= 2:
            pattern = [0, 1, 2, 3, 2, 1, 3, 2] * 2
            for s, k in enumerate(pattern):
                m = chord[k] + 12
                music.add(pluck(m), t0 + s * BEAT / 4, 0.9 if s % 4 == 0 else 0.6,
                          pan=0.35 if s % 2 else -0.35)
        if breakdown:
            music.add(riser(BAR), t0, 1.0)
    # sidechain: el bus musical «bombea» con cada kick
    sc = np.ones_like(music.L)
    tt = t_(BEAT)
    duck = 1 - 0.55 * np.exp(-tt * 9)
    for kt in kick_times:
        i = int(kt * SR)
        n = min(len(duck), len(sc) - i)
        sc[i:i + n] = np.minimum(sc[i:i + n], duck[:n])
    L = drums.L + music.L * sc
    R = drums.R + music.R * sc
    # hueco para la voz: -3 dB suaves en 1–4 kHz
    for ch in (L, R):
        mid = fft_filter(ch, 1000, 4000)
        ch -= 0.3 * mid
    # polvo de vinilo
    dust = (RNG.random(len(L)) > 0.99985) * RNG.uniform(-0.15, 0.15, len(L))
    L += fft_filter(dust, 1500, 9000)
    R += fft_filter(np.roll(dust, 517), 1500, 9000)
    # saturación + normalización + fundido final
    L, R = np.tanh(1.2 * L), np.tanh(1.2 * R)
    peak = max(np.abs(L).max(), np.abs(R).max())
    L, R = L / peak * 0.89, R / peak * 0.89
    fade = int(1.2 * SR)
    L[-fade:] *= np.linspace(1, 0, fade)
    R[-fade:] *= np.linspace(1, 0, fade)
    return L.astype(np.float32), R.astype(np.float32)


def write(out: str) -> str:
    L, R = render()
    st = np.stack([L, R], 1)
    pcm = (np.clip(st, -1, 1) * 32767).astype("<i2")
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if out.lower().endswith(".wav"):
        os.replace(tmp, out)
    else:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1.5",
                        "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "256k",
                        "-metadata", "title=Pulso Millón X", "-metadata", "artist=Millón X",
                        "-metadata", "copyright=CC0 1.0 (obra propia, generada por código)",
                        out], check=True)
        os.remove(tmp)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", nargs="?", default="resource/songs/millonx_pulse.mp3")
    write(ap.parse_args().out)
