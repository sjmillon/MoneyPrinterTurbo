# Millón X · preset de marca para MoneyPrinterTurbo

Rama `millonx-branding`. Vídeos verticales 9:16 con el estilo de Sergio Millón.

## Qué incluye
| Elemento | Valor |
|---|---|
| Paleta | fondo `#0C0E16`, blanco `#F5F5FA`, gris `#AAAFBE`, rojo `#FF4646` (pérdidas), verde `#3CE68C` (ganancias), amarillo `#FFC83C` (acento / "X"), violeta `#786EFF` (opinión) |
| Tipografía | **Anton** (titulares y subtítulos) y **Montserrat ExtraBold** (etiquetas). Ambas SIL OFL 1.1, licencias en `resource/fonts/licenses/` |
| Tarjetas por escena | fondo oscuro con halos difuminados del color de acento, barra superior de acento, antetítulo (kicker) gris, cifras grandes con sombra y firma "MILLÓN X" abajo |
| Subtítulos | Anton 78 px, blanco con contorno 6 px `#0C0E16`, posición al 80 % de la altura (bajo la tarjeta y por encima de la interfaz de X/TikTok), sin fondo, frase a frase |
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
