#!/usr/bin/env python3
"""Bild-Test: rendert Einzelbilder der Demo-Folge und vergleicht sie mit den Referenzbildern in tests/referenz/.
Fängt ungewollte Änderungen am Aussehen ab, bevor eine Folge damit online geht.

    python3 tools/bildtest.py          → vergleichen (Exit 1 bei Abweichung)
    python3 tools/bildtest.py --neu    → Referenzbilder neu erzeugen (nur nach gewollten Änderungen am Aussehen!)
"""
import glob
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMO = os.path.join(ROOT, "tests", "demo_stimmen")
REF = os.path.join(ROOT, "tests", "referenz")
ZEITEN = [0.5, 6.0, 11.05, 15.3, 18.5, 22.5]
GRENZE_MITTEL = 6.0     # mittlere Abweichung (0–255) pro Bild
GRENZE_ANTEIL = 0.06    # Anteil stark abweichender Pixel


def rendern(ziel):
    subprocess.run([sys.executable, os.path.join(ROOT, "engine.py"), os.path.join(DEMO, "episode.json"),
                    os.path.join(DEMO, "stimme.mp3"), os.path.join(ziel, "x.mp4"), "preview",
                    ",".join(str(z) for z in ZEITEN)], cwd=ziel, check=True, capture_output=True)
    return sorted(glob.glob(os.path.join(ziel, "prev_*.png")))


def klein(p):
    return np.asarray(Image.open(p).convert("RGB").resize((270, 480), Image.BILINEAR), dtype=np.float32)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        bilder = rendern(tmp)
        if "--neu" in sys.argv:
            os.makedirs(REF, exist_ok=True)
            for p in glob.glob(os.path.join(REF, "*.png")):
                os.remove(p)
            for p in bilder:
                Image.fromarray(klein(p).astype(np.uint8)).save(os.path.join(REF, os.path.basename(p)))
            print(f"{len(bilder)} Referenzbilder geschrieben")
            return
        fehler = 0
        for p in bilder:
            r = os.path.join(REF, os.path.basename(p))
            if not os.path.exists(r):
                print(f"FEHLT: Referenz {os.path.basename(p)} – mit --neu erzeugen"); fehler += 1; continue
            diff = np.abs(klein(p) - np.asarray(Image.open(r).convert("RGB"), dtype=np.float32))
            mittel, anteil = diff.mean(), (diff.max(axis=2) > 60).mean()
            ok = mittel <= GRENZE_MITTEL and anteil <= GRENZE_ANTEIL
            print(f"{'OK   ' if ok else 'ANDERS'} {os.path.basename(p)}  Mittel {mittel:.2f}  Anteil {anteil:.3f}")
            fehler += not ok
        sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
