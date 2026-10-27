# Licencias de la música (`resource/songs`)

| Archivo | Origen | Licencia | Uso en Millón X |
|---|---|---|---|
| `millonx_pulse.mp3` («Pulso Millón X») | Obra original sintetizada por código en este repo: `python -m app.branding.music resource/songs/millonx_pulse.mp3` (`app/branding/music.py`, numpy, semilla fija → archivo reproducible bit a bit). No usa muestras, loops, presets ni melodías de terceros. | **CC0 1.0** – dedicación al dominio público: https://creativecommons.org/publicdomain/zero/1.0/ | **Sí.** Pista por defecto del preset `--brand millonx` y del motor `app/branding/shorts.py` |
| `output000.mp3` … `output029.mp3` | Vienen del repo upstream harry0703/MoneyPrinterTurbo, sin autor ni licencia documentados | Desconocida | **No.** El preset Millón X no las usa (ni en modo aleatorio). No publicar vídeos con ellas |

Ficha de «Pulso Millón X»: 120 BPM, La menor (Am–F–C–G), 16 compases (33,5 s con la cola), estéreo 48 kHz, MP3 256 kbps, -14 LUFS.
