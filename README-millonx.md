# Millón X · preset de marca para MoneyPrinterTurbo

Rama `millonx-branding`. Vídeos verticales 9:16 con el estilo de Sergio Millón.

## Qué incluye
| Elemento | Valor |
|---|---|
| Paleta | basada en el perfil de X [@TheMillonX](https://x.com/TheMillonX): fondo marino `#141722` (de la americana del avatar, `#2D3142`), naranja llama `#F28C38` (Starship del banner, acento de marca y la "X"), azul cielo `#6FA3C7` (banner, opinión), blanco cálido `#F6F1E8`, gris `#B0B8C4`; rojo `#EB5757`/verde `#48C78E` sólo para pérdidas/ganancias |
| Tipografía | **Anton** (titulares y subtítulos) y **Montserrat ExtraBold** (etiquetas). Ambas SIL OFL 1.1, licencias en `resource/fonts/licenses/` |
| Tarjetas por escena | fondo oscuro con halos difuminados del color de acento, barra superior de acento, antetítulo (kicker) gris, cifras grandes con sombra y pastilla marino abajo con "MILLÓN X" (X en naranja) y el handle @TheMillonX |
| Subtítulos | Anton 78 px, blanco cálido `#F6F1E8` con contorno 6 px `#141722`, posición al 80 % de la altura (bajo la tarjeta y por encima de la interfaz de X/TikTok), sin fondo, frase a frase |
| Voz | `es-ES-AlvaroNeural` (Edge TTS), velocidad 1.1 por defecto, configurable con `--voice-rate` |
| Vídeo | sin transiciones de entrada, concatenación secuencial, imagen estática |
| Música | volumen 0,12 |
| Guion literal | `--literal-script`: el texto de `--video-script` se usa palabra por palabra; no se llama al LLM ni para el guion ni para los términos |

Cualquier opción que pases explícitamente en la CLI gana al preset.

## Uso
```bash
# 1. Tarjetas (ver tools/millonx_scenes_example.json)
python -m app.branding.cards tools/millonx_scenes_example.json storage/millonx_cards

# 2. Vídeo
python cli.py --brand millonx --literal-script \
  --video-subject "IPO Anthropic" \
  --video-script "Anthropic ha perdido ochenta mil millones en seis meses. ¿Burbuja? ..." \
  --video-source local \
  --video-materials storage/millonx_cards/card01.png,storage/millonx_cards/card02.png,storage/millonx_cards/card03.png \
  --video-clip-duration 5 --voice-rate 1.15
```
Formato de escena: `{"accent": "red", "kicker": "$ANT · IPO", "lines": [["-80.700 M$", 190, "red", 60]]}`; cada línea es `[texto, tamaño_máx, color, separación]`.

Consejo: escribe las cifras en el guion con letras ("ochenta mil millones") para que la voz las lea bien; en la tarjeta van en número.

## Archivos
- `app/branding/millonx.py`: preset (paleta, fuentes, voz, subtítulos, música).
- `app/branding/cards.py`: generador de tarjetas.
- `cli.py`: opciones `--brand` y `--literal-script`.
- `app/models/schema.py`, `app/services/task.py`: campo `literal_script` y salto del LLM.

## Origen de la marca
No hay manual de marca, logo ni tipografía definidos (revisado Notion y el disco). La paleta sale del avatar y el banner públicos de X de @TheMillonX; la tipografía sigue siendo Anton (titulares) + Montserrat ExtraBold (texto), ambas SIL OFL. Acentos admitidos en escenas: `orange`, `sky`, `red`, `green`, `navy`, `white`, `grey` (`yellow`/`violet` son alias de `orange`/`sky`).
