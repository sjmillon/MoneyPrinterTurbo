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
| Música | pista propia **«Pulso Millón X»** (`resource/songs/millonx_pulse.mp3`, generada con `app/branding/music.py`, CC0 1.0), `bgm_type=custom`, volumen 0,12. Ya no se usan las pistas de upstream |
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

Cifras: en el motor v2 escribe en `say` la misma cifra que sale en pantalla ("80.700 millones", "72.400"); Edge TTS es-ES la lee bien ("ochenta mil setecientos") y la voz y la tarjeta dicen lo mismo.

## Motor de shorts v2 (`app/branding/shorts.py`)
Es el renderizador recomendado para clips cortos con ritmo de creador. Es independiente del pipeline upstream (task → video.combine_videos → video.generate_video con moviepy), que solo sabe hacer tarjetas estáticas con zoom, subtítulos por frase en SRT, música a volumen fijo y nada de SFX. Aquí cada fotograma se dibuja con PIL a 1080x1920 y 30 fps y se envía por tubería a ffmpeg (libx264 crf 19, AAC 192k, faststart).

```bash
.venv/bin/python -m app.branding.shorts tools/millonx_ant_v2.json -o millonx_ant_v2.mp4 \
  --voice es-ES-AlvaroNeural --rate 15 --pitch +3Hz \
  --music resource/songs/millonx_pulse.mp3 --music-db -12 --max-duration 30 \
  --keep storage/millonx_ant_v2_work      # deja voice.wav, sfx.wav, mix.wav y timeline.json
```

| Técnica | Cómo está hecho | Referencia |
|---|---|---|
| Gancho en 0–0,5 s | La primera escena (`"hook": true`) abre con la cifra ya en pantalla (el fotograma 0 está limpio y sirve de miniatura), un slam 1,28→1, una sacudida, un flash y un impacto grave. La voz empieza en 0,0 s | asendify.co/blog/short-form-retention-editing; soundcache.io/blog/anatomy-of-a-viral-edit; hilo de MrBeast (threadreaderapp 1688598816801656832) |
| Subtítulos karaoke | Tiempos por palabra de Edge TTS (WordBoundary), grupos de ≤3 palabras / 16 caracteres que se cortan en la puntuación, Anton en mayúsculas con trazo y sombra. La palabra activa va en #F28C38 con pop, más un emoji por palabra clave | montage.app/blog/hormozi-style-editing; choppity.com (estilo Hormozi); findclout.com/blog/clip-editing-guide |
| Jump-cut de audio | Los silencios se recortan a 0,2 s (0,3 s entre escenas) con fundidos de 6 ms y los tiempos se recalculan | Lenguaje de clippers: openclip.app/clipping/clipper-workflow |
| Movimiento constante | Ken Burns por escena, punch-in al entrar cada escena (10 %), cada línea (3,5 %) y cada palabra `punch` (6 %), deriva suave y whip-pan con desenfoque direccional en los cortes | writepanda.ai/blog/hormozi-style-shorts-editing |
| Cifras animadas | `count: {from, dur}` con ease-out y separador de miles con punto | motioncheatcode.com/guides/animated-charts-and-counters; Humphrey Yang (fortune.com 2020/03/21) |
| SFX | Sintetizados con numpy en `app/branding/sfx.py` (CC0, hechos aquí): impacto, whoosh en cada corte, pops con variación de tono al aparecer cada línea, ticks durante los contadores y un riser antes del cierre | woven.video/guides/add-sound-effects-to-video; faviovazquez.github.io/showtime/docs/sound-design.html |
| Música con ducking | Pista propia «Pulso Millón X» desde el segundo 0 (`--music-start`), `--music-db -12` y sidechaincompress con la voz como llave (ratio 4, ataque 20 ms, release 400 ms). La música queda unos 17 dB por debajo de la voz (medido: voz -17,6 LUFS, música ducked -34,3 LUFS) y el máster sale con loudnorm a -14 LUFS | Guía de ducking de CapCut; tryproduck/produck-skills SOUND.md |
| Barra de progreso | Barra de 12 px arriba (pista navy, relleno naranja, punto blanco). Junto con la píldora de kicker indica en qué parte del vídeo estás | videohead.io; writepanda.ai |
| Loop | Los últimos 5 fotogramas se funden con el inicio, sin subtítulos y con whip | asendify.co; soundcache.io |
| B-roll opcional | `"broll": "términos"` busca primero en la carpeta local `resource/broll/millonx/` (etiquetas en `broll.json`, sin API) y solo después en Pexels si hay `pexels_api_keys`. `"broll_file": "nombre"` fija un archivo. Se recorta para cubrir el lienzo, se repite en bucle y se oscurece con un tinte navy (`"broll_dim"`, 0–1, por defecto 0,55) para que el texto se lea | Graham Stephan: B-roll funcional (blog.editorduel.com) |
| Gráficas animadas | `"chart"` por escena (`app/branding/charts.py`): barras horizontales (`hbars`) o columnas (`vbars`) en un panel marino, cada barra crece cuando la voz dice su `cue` con contador y ticks, insignia opcional (`badge`, p. ej. "x14") con flecha. `"source"` pinta la fuente pequeña sobre la firma | motioncheatcode.com/guides/animated-charts-and-counters; estilo Humphrey Yang / Graham Stephan |

La firma (píldora MILLÓN X / @TheMillonX) y la paleta salen de `app/branding/millonx.py`.

### Formato de escenas v2
```json
{"scenes": [
  {"say": "Anthropic ha perdido 80.700 millones en seis meses. ¿Burbuja?",
   "hook": true, "accent": "red", "kicker": "$ANT · IPO ANTHROPIC", "punch": ["Burbuja"],
   "lines": [{"text": "-80.700 M$", "size": 200, "color": "red", "cue": "Anthropic"},
             {"text": "72.400 M$", "size": 180, "color": "orange", "cue": "72.400",
              "count": {"from": 0, "dur": 0.9}}]}
]}
```
- `say`: el texto literal que se locuta. El guion final es la concatenación de todos los `say`.
- `cue`: la palabra del `say` en la que aparece la línea.
- `punch`: palabras que disparan un punch-in y un pop.
- Las líneas en formato lista antiguo (`[texto, tamaño, color, separación]`) también se aceptan.

### Límites conocidos
- Edge TTS no tiene estilos expresivos y en es-ES solo hay una voz masculina (Álvaro). La energía sale de la velocidad (+15 %), el tono (+3 Hz), la EQ con compresión y el recorte de silencios.
- El motor no pasa por `cli.py` ni por la WebUI.

## v4 · gráficas y B-roll propio (sin Pexels)
Pexels tiene pausada la emisión de claves de API, así que el motor ya no depende de ninguna clave:

```bash
python -m app.branding.shorts tools/millonx_ant_v4.json -o millonx_ant_v4.mp4 \
  --broll-dir resource/broll/millonx --keep storage/millonx_ant_v4_work
```

Ejemplo de escena con gráfica (solo cifras reales del S-1, el motor no inventa datos):
```json
{"say": "Pérdida operativa real: 693 millones.", "source": "Fuente: S-1 Anthropic (SEC)",
 "chart": {"type": "hbars", "y": 790, "h": 560, "max": 80700, "bars": [
   {"label": "Pérdida neta", "value": 80700, "color": "red", "prefix": "-", "instant": true, "count": false},
   {"label": "Apunte contable", "value": 72400, "color": "orange", "instant": true, "count": false},
   {"label": "Pérdida operativa", "value": 693, "color": "green", "cue": "693", "note": "< 1 % del total"}]}}
```
Campos de barra: `label`, `value`, `color`, `cue` (palabra de la voz en la que crece), `instant` (ya está al entrar), `count` (anima la cifra), `prefix`, `fmt` (`"≈{v} M$"`), `note` (texto junto a barras diminutas, que además llevan un halo que late). Con `chart` las frases se maquetan encima del panel.

B-roll: cualquier `.mp4/.mov/.webm` en la carpeta sirve. Añade sus etiquetas en `broll.json` y documenta el origen en `LICENSES.md`. El de $ANT está generado con IA para el canal (centro de datos, cohete genérico, Tierra en red y sala de trading), sin personas, logos ni texto. Ver `resource/broll/millonx/LICENSES.md`.

## Música sin derechos de terceros
- **Pista:** «Pulso Millón X», `resource/songs/millonx_pulse.mp3`. Electrónica / lo-fi enérgica a 120 BPM en La menor (Am–F–C–G), 32 s + cola: kick a negras con sidechain (bombeo), palmada en 2 y 4, charles con swing, bajo sierra filtrado, pad supersaw, arpegio pluck a semicorcheas, saturación suave y polvo de vinilo. Lleva un hueco de -3 dB en 1–4 kHz para que la voz respire.
- **Origen:** obra original sintetizada por `app/branding/music.py` (solo numpy + ffmpeg para codificar). Sin muestras, loops ni presets de terceros. La semilla es fija, así que `python -m app.branding.music` regenera el mismo archivo bit a bit, y el motor la regenera si falta.
- **Licencia:** CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/). Como es creación propia, no hay ningún tercero que pueda reclamarla ni coincidencias en Content ID. Detalle en `resource/songs/LICENSES.md`.
- Las pistas `output0xx.mp3` de upstream no tienen licencia documentada y el preset Millón X ya no las usa.

## Archivos
- `app/branding/music.py`: síntesis de la pista «Pulso Millón X» (CC0).
- `resource/songs/millonx_pulse.mp3` y `resource/songs/LICENSES.md`: pista y licencias.
- `app/branding/millonx.py`: preset (paleta, fuentes, voz, subtítulos, música).
- `app/branding/cards.py`: generador de tarjetas.
- `app/branding/shorts.py`: motor de shorts v2 (karaoke, cámara, SFX, ducking, progreso, contadores, B-roll).
- `app/branding/sfx.py`: síntesis de efectos de sonido CC0.
- `tools/millonx_ant_v2.json`: escenas del vídeo $ANT v2/v3 (guion literal).
- `tools/millonx_ant_v4.json`: $ANT v4 = v3 + gráficas + B-roll propio.
- `app/branding/charts.py`: gráficas animadas (barras, columnas, insignia, fuente).
- `resource/broll/millonx/`: B-roll propio generado con IA, `broll.json` (etiquetas y prompts) y `LICENSES.md`.
- `cli.py`: opciones `--brand` y `--literal-script`.
- `app/models/schema.py`, `app/services/task.py`: campo `literal_script` y salto del LLM.

## Origen de la marca
No hay manual de marca, logo ni tipografía definidos (revisado Notion y el disco). La paleta sale del avatar y el banner públicos de X de @TheMillonX; la tipografía sigue siendo Anton (titulares) + Montserrat ExtraBold (texto), ambas SIL OFL. Acentos admitidos en escenas: `orange`, `sky`, `red`, `green`, `navy`, `white`, `grey` (`yellow`/`violet` son alias de `orange`/`sky`).

## Binance v1 · hackeo del 29-30 oct 2026
```bash
python -m app.branding.shorts tools/millonx_binance_v1.json -o millonx_binance_v1.mp4 \
  --broll-dir resource/broll/millonx --keep storage/millonx_binance_v1_work
```
Mismo motor, transiciones, voz y música que $ANT v4. Cifras solo confirmadas (comunicado oficial de Binance: impacto estimado ~6.300 M$, ~3.000 M$ congelados; récord anterior Bybit 2025 ~1.500 M$). La autoría (Corea del Norte / TraderTraitor) se presenta como sospecha de TRM Labs y Chainalysis, no como hecho. B-roll nuevo generado con IA: `vault.mp4`, `intrusion.mp4`, `drain.mp4`, `frozen.mp4` (sin personas, logos ni texto).
