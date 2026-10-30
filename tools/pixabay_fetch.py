"""Descarga B-roll REAL de Pixabay (licencia Pixabay: uso gratuito, comercial incluido, sin atribución
obligatoria) y lo deja listo para el motor de shorts.

Uso::

    PIXABAY_API_KEY=... python tools/pixabay_fetch.py 88697 124287 ... --use "MSTR v1"

- Lee la clave SOLO de la variable de entorno ``PIXABAY_API_KEY`` (nunca se guarda en el repo).
- Re-codifica cada clip a 1080x1920 (recorte central 9:16), H.264 crf 23, sin audio, máx. 12 s.
- Añade la entrada a ``resource/broll/millonx/broll.json`` y una fila a ``LICENSES.md`` con autor,
  id y página de Pixabay para poder demostrar el origen.
"""
import argparse, json, os, subprocess, sys, tempfile
import requests

FOLDER = "resource/broll/millonx"
UA = {"User-Agent": "MillonX-shorts/1.0"}


def fetch(vid, key):
    r = requests.get("https://pixabay.com/api/videos/", params={"key": key, "id": vid},
                     headers=UA, timeout=30)
    r.raise_for_status()
    hits = r.json()["hits"]
    if not hits:
        raise SystemExit(f"Pixabay {vid}: no encontrado")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--use", default="")
    ap.add_argument("--max", type=float, default=12.0)
    a = ap.parse_args()
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        sys.exit("Falta PIXABAY_API_KEY")
    mpath = os.path.join(FOLDER, "broll.json")
    meta = json.load(open(mpath, encoding="utf-8"))
    rows = []
    for vid in a.ids:
        h = fetch(vid, key)
        v = h["videos"].get("medium") or {}
        if not v.get("url"):
            v = h["videos"]["large"]
        fn = f"pixabay_{h['id']}.mp4"
        out = os.path.join(FOLDER, fn)
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            with requests.get(v["url"], headers=UA, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_content(1 << 20):
                    tmp.write(chunk)
            tmp.flush()
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp.name, "-t", str(a.max), "-an",
                            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
                            "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv420p",
                            out], check=True)
        tags = [t.strip() for t in h["tags"].split(",")]
        meta[fn] = {"tags": tags, "source": "Pixabay", "pixabay_id": h["id"], "author": h["user"],
                    "page": h["pageURL"], "license": "Pixabay Content License (https://pixabay.com/service/license-summary/)"}
        rows.append(f"| `{fn}` | {a.use} | Pixabay #{h['id']} · autor: {h['user']} · {h['pageURL']} · Licencia de contenido de Pixabay |")
        print(f"[pixabay] {fn} <- {h['pageURL']} ({h['user']})")
    json.dump(meta, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lic = os.path.join(FOLDER, "LICENSES.md")
    txt = open(lic, encoding="utf-8").read()
    head = "\n## Metraje real de Pixabay\n\n| Archivo | Uso | Origen |\n|---|---|---|\n"
    if "## Metraje real de Pixabay" not in txt:
        txt = txt.rstrip("\n") + "\n" + head + "\n".join(rows) + "\n\n" + (
            "- Licencia de contenido de Pixabay: uso gratuito, también comercial, sin atribución obligatoria "
            "(se registra igualmente). No se vende el clip suelto ni se presenta como propio; no se usan "
            "personas reconocibles ni marcas en un contexto que sugiera respaldo.\n"
            "- Re-codificados con `tools/pixabay_fetch.py` a 1080x1920 (recorte 9:16), H.264 crf 23, sin audio, máx. 12 s.\n")
    else:
        a_, b_ = txt.split("## Metraje real de Pixabay", 1)
        tbl_end = b_.find("\n\n", b_.find("|---|"))
        b_ = b_[:tbl_end] + "\n" + "\n".join(rows) + b_[tbl_end:]
        txt = a_ + "## Metraje real de Pixabay" + b_
    open(lic, "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    main()
