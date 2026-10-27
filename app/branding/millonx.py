"""Preset de marca "Millón X".

Centraliza colores, tipografías, estilo de subtítulos, voz y mezcla de audio
para que todos los vídeos de Sergio Millón salgan con el mismo acabado.
Las tarjetas por escena se generan con :mod:`app.branding.cards`.
"""
from __future__ import annotations

import os
from typing import Any, Iterable

from app.utils import utils

# --- Paleta -----------------------------------------------------------------
BG = (12, 14, 22)          # fondo casi negro azulado
WHITE = (245, 245, 250)
GREY = (170, 175, 190)
RED = (255, 70, 70)        # pérdidas / alerta
GREEN = (60, 230, 140)     # ganancias / dato bueno
YELLOW = (255, 200, 60)    # acento de marca (el "X")
VIOLET = (120, 110, 255)   # tesis / opinión

ACCENTS = {"red": RED, "green": GREEN, "yellow": YELLOW, "violet": VIOLET, "white": WHITE, "grey": GREY}

# --- Tipografías (SIL OFL 1.1, licencias en resource/fonts/licenses) -------
HEADLINE_FONT = "Anton-Regular.ttf"
BODY_FONT = "Montserrat-VariableFont_wght.ttf"


def font_path(name: str) -> str:
    return os.path.join(utils.font_dir(), name)


MILLONX: dict[str, Any] = {
    # Voz
    "voice_name": "es-ES-AlvaroNeural-Male",
    "voice_rate": 1.1,          # configurable con --voice-rate
    "voice_volume": 1.0,
    "video_language": "es-ES",
    # Vídeo
    "video_aspect": "9:16",
    "video_transition_mode": None,   # sin transiciones de entrada
    "video_concat_mode": "sequential",
    "image_motion": "static",
    # Música
    "bgm_volume": 0.12,
    # Subtítulos
    "subtitle_enabled": True,
    "font_name": HEADLINE_FONT,
    "font_size": 78,
    "text_fore_color": "#FFFFFF",
    "stroke_color": "#0C0E16",
    "stroke_width": 6,
    "subtitle_position": "custom",
    "custom_position": 80.0,     # bajo las tarjetas, por encima de la UI de X/TikTok
    "subtitle_display_mode": "sentence",
    "subtitle_animation": "none",
    "text_background_color": False,
}

BRANDS = {"millonx": MILLONX}


def apply_brand(params_kwargs: dict, brand: str, explicit: Iterable[str] = ()) -> dict:
    """Rellena ``params_kwargs`` con el preset sin pisar lo que el usuario pasó a mano."""
    preset = BRANDS.get((brand or "").lower())
    if preset is None:
        raise ValueError(f"unknown brand preset: {brand}")
    explicit = set(explicit)
    for key, value in preset.items():
        if key not in explicit:
            params_kwargs[key] = value
    return params_kwargs
