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
# Sacada de la identidad pública de Sergio en X (@TheMillonX), no inventada:
#  - avatar: americana azul marino (#2D3142 dominante) y camisa blanca
#  - banner: despegue de Starship, llama naranja (#D99350 medio) y cielo azul (#57809C)
# Rojo/verde se mantienen sólo como semántica de datos (pérdida / ganancia).
NAVY = (45, 49, 66)        # #2D3142, americana del avatar
BG = (20, 23, 34)          # #141722, marino oscurecido para fondo de vídeo
WHITE = (246, 241, 232)    # #F6F1E8, blanco cálido (nubes del banner)
GREY = (176, 184, 196)     # #B0B8C4
ORANGE = (242, 140, 56)    # #F28C38, llama del Starship (acento de marca)
SKY = (111, 163, 199)      # #6FA3C7, cielo del banner (tesis / opinión)
RED = (235, 87, 87)        # #EB5757 pérdidas
GREEN = (72, 199, 142)     # #48C78E ganancias

# Alias de compatibilidad: "yellow" -> naranja de marca, "violet" -> azul cielo
YELLOW = ORANGE
VIOLET = SKY
ACCENTS = {"red": RED, "green": GREEN, "orange": ORANGE, "sky": SKY, "navy": NAVY,
           "yellow": ORANGE, "violet": SKY, "white": WHITE, "grey": GREY}

HANDLE = "@TheMillonX"     # firma en tarjetas

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
    # Música: pista propia «Pulso Millón X» (app/branding/music.py, CC0, sin
    # derechos de terceros). Nunca se usa el sorteo de resource/songs de upstream.
    "bgm_type": "custom",
    "bgm_file": "millonx_pulse.mp3",
    "bgm_volume": 0.12,
    # Subtítulos
    "subtitle_enabled": True,
    "font_name": HEADLINE_FONT,
    "font_size": 78,
    "text_fore_color": "#F6F1E8",
    "stroke_color": "#141722",
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
        # si el usuario eligió otro modo de música, no le colamos la pista de marca
        if key == "bgm_file" and "bgm_type" in explicit:
            continue
        if key not in explicit:
            params_kwargs[key] = value
    return params_kwargs
