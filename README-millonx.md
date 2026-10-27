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

## Motor de shorts v2 (`app/branding/shorts.py`)
Es el renderizador recomendado para clips cortos con ritmo de creador. Es independiente del pipeline upstream (task → video.combine_videos → video.generate_video con moviepy), que solo sabe hacer tarjetas estáticas con zoom, subtítulos por frase en SRT, música a volumen fijo y nada de SFX. Aquí cada fotograma se dibuja con PIL a 1080x1920 y 30 fps y se envía por tubería a ffmpeg (libx264 crf 19, AAC 192k, faststart).

```bash
.venv/bin/python -m app.branding.shorts tools/millonx_ant_v2.json -o millonx_ant_v2.mp4 \
  --voice es-ES-AlvaroNeural --rate 15 --pitch +3Hz \
  --music resource/songs/output019.mp3 --music-db -3 --max-duration 30 \
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
| Música con ducking | sidechaincompress con la voz como llave (ratio 4, ataque 20 ms, release 400 ms). La música queda unos 12 dB por debajo de la voz y el máster sale con loudnorm a -14 LUFS | Guía de ducking de CapCut; tryproduck/produck-skills SOUND.md |
| Barra de progreso | Barra de 12 px arriba (pista navy, relleno naranja, punto blanco). Junto con la píldora de kicker indica en qué parte del vídeo estás | videohead.io; writepanda.ai |
| Loop | Los últimos 5 fotogramas se funden con el inicio, sin subtítulos y con whip | asendify.co; soundcache.io |
| B-roll opcional | `"broll": "términos"` (Pexels, solo si `pexels_api_keys` está configurado en config.toml) o `"broll_file": "ruta.mp4"`. Se recorta para cubrir el lienzo, se repite en bucle y se oscurece con un tinte navy para que el texto se lea | Graham Stephan: B-roll funcional (blog.editorduel.com) |

La firma (píldora MILLÓN X / @TheMillonX) y la paleta salen de `app/branding/millonx.py`.

### Formato de escenas v2
```json
{"scenes": [
  {"say": "Anthropic ha perdido 80.000 millones en seis meses. ¿Burbuja?",
   "hook": true, "accent": "red", "kicker": "$ANT · IPO ANTHROPIC", "punch": ["Burbuja"],
   "lines": [{"text": "-80.700 M$", "size": 200, "color": "red", "cue": "Anthropic"},
             {"text": "72.400 M$", "size": 180, "color": "orange", "cue": "72.000",
              "count": {"from": 0, "dur": 0.9}}]}
]}
```
- `say`: el texto literal que se locuta. El guion final es la concatenación de todos los `say`.
- `cue`: la palabra del `say` en la que aparece la línea.
- `punch`: palabras que disparan un punch-in y un pop.
- Las líneas en formato lista antiguo (`[texto, tamaño, color, separación]`) también se aceptan.

### Límites conocidos
- Edge TTS no tiene estilos expresivos y en es-ES solo hay una voz masculina (Álvaro). La energía sale de la velocidad (+15 %), el tono (+3 Hz), la EQ con compresión y el recorte de silencios.
- La música de `resource/songs` viene de upstream y no tiene licencia documentada. Para publicar, usa una pista con licencia propia.
- El motor no pasa por `cli.py` ni por la WebUI.

## Archivos
- `app/branding/millonx.py`: preset (paleta, fuentes, voz, subtítulos, música).
- `app/branding/cards.py`: generador de tarjetas.
- `app/branding/shorts.py`: motor de shorts v2 (karaoke, cámara, SFX, ducking, progreso, contadores, B-roll).
- `app/branding/sfx.py`: síntesis de efectos de sonido CC0.
- `tools/millonx_ant_v2.json`: escenas del vídeo $ANT v2 (guion literal).
- `cli.py`: opciones `--brand` y `--literal-script`.
- `app/models/schema.py`, `app/services/task.py`: campo `literal_script` y salto del LLM.

## Origen de la marca
No hay manual de marca, logo ni tipografía definidos (revisado Notion y el disco). La paleta sale del avatar y el banner públicos de X de @TheMillonX; la tipografía sigue siendo Anton (titulares) + Montserrat ExtraBold (texto), ambas SIL OFL. Acentos admitidos en escenas: `orange`, `sky`, `red`, `green`, `navy`, `white`, `grey` (`yellow`/`violet` son alias de `orange`/`sky`).
