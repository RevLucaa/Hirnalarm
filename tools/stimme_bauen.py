#!/usr/bin/env python3
"""Figurenstimmen: Skript in Sprecher-Blöcke zerlegen und die erzeugten Teile zu stimme.mp3 zusammenfügen.

skript.txt-Format (eine Zeile pro Wortbeitrag, Sprecher = Kurzname aus stimmen.json oder „Erzähler“):
    Erzähler: [excited] Kalle hat Mannis Gürtel geklaut!
    Manni: Den hol ich mir zurück.
Zeilen ohne „Name:“ gehören zum Erzähler.

1) Blöcke anzeigen (was an ElevenLabs geht, mit Credits):
       python3 tools/stimme_bauen.py bloecke episodes/F12_xyz
   → JSON-Liste [{nr, sprecher, voice_id, text, zeichen}], Exit 1 wenn > max_credits_pro_video.
2) Pro Block creative_generate_speech (model eleven_v4, voice_id aus der Liste, generations_count 1),
   Ergebnis als teile/01.mp3, teile/02.mp3 … in den Episoden-Ordner laden.
3) Zusammenfügen (Lautheit angleichen, kurze Pausen, Tempo auf 55–57 s):
       python3 tools/stimme_bauen.py zusammenfuegen episodes/F12_xyz   (--ohne-tempo für kurze Proben)
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BESETZUNG = json.load(open(os.path.join(ROOT, "stimmen.json"), encoding="utf-8"))
ZEILE = re.compile(r"^\s*([A-Za-zÄÖÜäöüß\-]+)\s*:\s*(.*)$")


def zeilen(skript):
    """(sprecher, text) je Zeile; Sprecherwechsel nur bei bekanntem Namen, sonst Erzähler."""
    out = []
    for z in open(skript, encoding="utf-8").read().splitlines():
        if not z.strip():
            continue
        m = ZEILE.match(z)
        if m and m.group(1) in BESETZUNG["stimmen"]:
            out.append((m.group(1), m.group(2).strip()))
        else:
            out.append(("Erzähler", z.strip()))
    return out


def bloecke(ordner):
    bl = []
    for sp, text in zeilen(os.path.join(ordner, "skript.txt")):
        if bl and bl[-1]["sprecher"] == sp:
            bl[-1]["text"] += " " + text
        else:
            bl.append({"sprecher": sp, "text": text})
    for i, b in enumerate(bl, 1):
        b["nr"] = i
        b["voice_id"] = BESETZUNG["stimmen"][b["sprecher"]]["voice_id"]
        b["zeichen"] = len(b["text"])
        b["credits"] = round(b["zeichen"] * BESETZUNG["stimmen"][b["sprecher"]].get("faktor", 1.0))
    return bl


def dauer(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip())


def zusammenfuegen(ordner, tempo_anpassen=True):
    bl = bloecke(ordner)
    teile = sorted(glob.glob(os.path.join(ordner, "teile", "*.mp3")))
    if len(teile) != len(bl):
        sys.exit(f"{len(bl)} Blöcke, aber {len(teile)} Dateien in teile/ – bitte prüfen")
    tmp = os.path.join(ordner, "teile")
    norm = []
    for i, t in enumerate(teile):
        n = os.path.join(tmp, f"_n{i:02d}.wav")
        # gleiche Lautheit für alle Stimmen, Stille an den Rändern weg
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", t, "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "44100", "-ac", "1", n], check=True)
        norm.append(n)
    pause = os.path.join(tmp, "_pause.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", "0.35", pause], check=True)
    liste = os.path.join(tmp, "_liste.txt")
    with open(liste, "w") as f:
        for i, n in enumerate(norm):
            if i:
                f.write(f"file '{os.path.abspath(pause)}'\n")
            f.write(f"file '{os.path.abspath(n)}'\n")
    roh = os.path.join(tmp, "_roh.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", liste, roh], check=True)
    d = dauer(roh)
    tempo = 1.0
    if not tempo_anpassen:
        pass
    elif d < 55:
        tempo = max(0.88, d / 56)
    elif d > 57:
        tempo = min(1.12, d / 56.5)
    ziel = os.path.join(ordner, "stimme.mp3")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", roh, "-af", f"atempo={tempo:.4f}",
                    "-b:a", "192k", ziel], check=True)
    for p in glob.glob(os.path.join(tmp, "_*")):
        os.remove(p)
    print(json.dumps({"stimme": ziel, "roh_s": round(d, 2), "tempo": round(tempo, 3),
                      "dauer_s": round(dauer(ziel), 2), "credits": sum(b["credits"] for b in bl)}, ensure_ascii=False))
    if tempo_anpassen and dauer(ziel) > 57.5:
        print("WARNUNG: Stimme länger als 57,5 s – Skript kürzen", file=sys.stderr)


def main():
    ohne_tempo = "--ohne-tempo" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--ohne-tempo"]
    if len(sys.argv) != 3 or sys.argv[1] not in ("bloecke", "zusammenfuegen"):
        sys.exit(__doc__)
    ordner = sys.argv[2].rstrip("/")
    if sys.argv[1] == "bloecke":
        bl = bloecke(ordner)
        summe = sum(b["credits"] for b in bl)
        print(json.dumps(bl, ensure_ascii=False, indent=1))
        grenze = BESETZUNG["max_credits_pro_video"]
        print(f"{len(bl)} Blöcke, ca. {summe} Credits (Grenze {grenze})", file=sys.stderr)
        sys.exit(1 if summe > grenze else 0)
    zusammenfuegen(ordner, tempo_anpassen=not ohne_tempo)


if __name__ == "__main__":
    main()
