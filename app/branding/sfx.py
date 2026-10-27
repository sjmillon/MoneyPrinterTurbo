"""Efectos de sonido sintetizados (dominio público / CC0, generados aquí).

No dependen de bancos externos: cada efecto se calcula con numpy a 48 kHz mono
en float32 [-1, 1]. Así el repo no arrastra licencias de terceros.

- ``impact``: golpe grave (sub 55 Hz con caída de tono + click) para el gancho.
- ``whoosh``: ruido filtrado con barrido y envolvente en campana para los cortes.
- ``pop``: blip corto con caída de tono para la aparición de cifras/frases.
- ``tick``: click seco para los contadores.
- ``riser``: subida de ruido + tono antes de la pregunta final.
"""
from __future__ import annotations

import numpy as np

SR = 48000


def _t(dur: float) -> np.ndarray:
    return np.arange(int(SR * dur), dtype=np.float32) / SR


def _lowpass(x: np.ndarray, cutoff: np.ndarray | float) -> np.ndarray:
    """Filtro paso bajo de un polo con frecuencia de corte variable."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=np.float32), x.shape)
    a = np.exp(-2.0 * np.pi * cutoff / SR).astype(np.float32)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # efectos de <1 s: el bucle es barato
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def _norm(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(x)) or 1.0)
    return (x / m * peak).astype(np.float32)


def impact(dur: float = 0.9, seed: int = 1) -> np.ndarray:
    t = _t(dur)
    f = 40 + 90 * np.exp(-t * 18)                       # 130 Hz -> 40 Hz
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t * 5.5)
    rng = np.random.default_rng(seed)
    click = rng.standard_normal(len(t)).astype(np.float32) * np.exp(-t * 90)
    click = _lowpass(click, 3500)
    x = body + 0.6 * click
    return _norm(np.tanh(2.2 * x))


def whoosh(dur: float = 0.42, seed: int = 2, rising: bool = True) -> np.ndarray:
    t = _t(dur)
    rng = np.random.default_rng(seed)
    n = rng.standard_normal(len(t)).astype(np.float32)
    p = t / dur
    sweep = (300 + 5200 * p ** 1.6) if rising else (5500 - 5200 * p ** 0.7)
    x = _lowpass(n, sweep) - 0.6 * _lowpass(n, 180)     # banda: quita graves
    env = np.sin(np.pi * np.clip(p, 0, 1)) ** 2 * (p < 1)
    env = env * np.where(p < 0.72, 1.0, np.exp(-(p - 0.72) * 9))
    return _norm(x * env, 0.85)


def pop(freq: float = 620.0, dur: float = 0.12) -> np.ndarray:
    t = _t(dur)
    f = freq * (1 + 1.4 * np.exp(-t * 60))
    phase = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(phase) * np.exp(-t * 38) * (1 - np.exp(-t * 2500))
    return _norm(x, 0.8)


def tick(freq: float = 2400.0, dur: float = 0.035) -> np.ndarray:
    t = _t(dur)
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t * 160)
    return _norm(x, 0.7)


def riser(dur: float = 0.8, seed: int = 3) -> np.ndarray:
    t = _t(dur)
    p = t / dur
    rng = np.random.default_rng(seed)
    n = _lowpass(rng.standard_normal(len(t)).astype(np.float32), 400 + 6000 * p ** 2)
    f = 180 + 520 * p ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = p ** 2.2
    return _norm((0.7 * n + 0.35 * tone) * env, 0.75)


class Track:
    """Pista de efectos: se colocan sonidos alineando su *golpe* con un instante."""

    def __init__(self, duration: float):
        self.buf = np.zeros(int(SR * (duration + 2)), dtype=np.float32)

    def place(self, sound: np.ndarray, at: float, gain_db: float = 0.0, hit: float = 0.0):
        """``hit``: segundos desde el inicio del efecto hasta su pico (p. ej. whoosh)."""
        start = int(round((at - hit) * SR))
        g = 10 ** (gain_db / 20)
        s = sound * g
        if start < 0:
            s = s[-start:]
            start = 0
        end = min(len(self.buf), start + len(s))
        self.buf[start:end] += s[: end - start]

    def render(self, duration: float) -> np.ndarray:
        return np.clip(self.buf[: int(SR * duration)], -1, 1)
