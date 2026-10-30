# B-roll Millón X · origen y licencia

| Archivo | Uso en $ANT v4 | Origen |
|---|---|---|
| `datacenter.mp4` | gancho (escena 1) | Generado con IA (Grok Imagine, herramienta GenerateVideo de Grok Bot), 27-oct-2026 |
| `rocket.mp4` | "A SpaceX también la daban por muerta" (escena 5) | Generado con IA, 27-oct-2026 |
| `earth.mp4` | "cuánto cambian el mundo" (escena 6) | Generado con IA, 27-oct-2026 |
| `trading.mp4` | "En noviembre sale al Nasdaq" (escena 7) | Generado con IA, 27-oct-2026 |
| `vault.mp4` | Binance v1, gancho (cámara acorazada abriéndose a la oscuridad) | Generado con IA, 30-oct-2026 |
| `intrusion.mp4` | Binance v1, "entraron por el portátil" (intrusión abstracta, portátil sin nadie) | Generado con IA, 30-oct-2026 |
| `drain.mp4` | Binance v1, "Corea del Norte" (monedas abstractas sin símbolos drenándose) | Generado con IA, 30-oct-2026 |
| `frozen.mp4` | Binance v1, "retiros parados" (candado y cadena sobre pantalla helada sin texto) | Generado con IA, 30-oct-2026 |

- Clips generados con IA: material creado para Millón X a partir de prompts propios (ver `broll.json`), sin metraje de agencias ni de noticias. El metraje real de stock está en la sección de Pixabay.
- Los prompts prohíben personas reales, texto legible, logos (incluido el de Binance o cualquier exchange), banderas, insignias y nombres de bolsa o de empresa. El cohete es genérico, no un vehículo de SpaceX.
- Re-codificados con ffmpeg (H.264 crf 22, sin audio) a 720x1280 y 6 s. El motor los recorta a 9:16, los repite en bucle y los oscurece con tinte marino (`broll_dim`).
- Uso: propio de Millón X. Revisa los términos de uso de la herramienta de generación si se usan fuera del canal.

## Metraje real de Pixabay

| Archivo | Uso | Origen |
|---|---|---|
| `pixabay_88697.mp4` | MSTR v1 (30-oct-2026) | Pixabay #88697 · autor: Gam-Ol · https://pixabay.com/videos/id-88697/ · Licencia de contenido de Pixabay |
| `pixabay_27453.mp4` | MSTR v1 (30-oct-2026) | Pixabay #27453 · autor: RoyBuri · https://pixabay.com/videos/id-27453/ · Licencia de contenido de Pixabay |
| `pixabay_124287.mp4` | MSTR v1 (30-oct-2026) | Pixabay #124287 · autor: BZprod · https://pixabay.com/videos/id-124287/ · Licencia de contenido de Pixabay |
| `pixabay_173138.mp4` | MSTR v1 (30-oct-2026) | Pixabay #173138 · autor: Eartvideos · https://pixabay.com/videos/id-173138/ · Licencia de contenido de Pixabay |
| `pixabay_3134.mp4` | MSTR v1 (30-oct-2026) | Pixabay #3134 · autor: Life-Of-Vids · https://pixabay.com/videos/id-3134/ · Licencia de contenido de Pixabay |
| `pixabay_120177.mp4` | MSTR v1 (30-oct-2026) | Pixabay #120177 · autor: BilawalOnwa · https://pixabay.com/videos/id-120177/ · Licencia de contenido de Pixabay |
| `pixabay_166289.mp4` | MSTR v1 (30-oct-2026) | Pixabay #166289 · autor: Dimitri_K · https://pixabay.com/videos/id-166289/ · Licencia de contenido de Pixabay |

- Licencia de contenido de Pixabay: uso gratuito, también comercial, sin atribución obligatoria (se registra igualmente). No se vende el clip suelto ni se presenta como propio; no se usan personas reconocibles ni marcas en un contexto que sugiera respaldo.
- Re-codificados con `tools/pixabay_fetch.py` a 1080x1920 (recorte 9:16), H.264 crf 23, sin audio, máx. 12 s.
