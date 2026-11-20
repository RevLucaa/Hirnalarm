#!/usr/bin/env python3
"""Prüft alle Episoden und liga.json auf typische Fehler, bevor etwas gerendert oder gepostet wird.

Aufruf:  python3 tools/pruefen.py            (alles)
         python3 tools/pruefen.py F10_...    (nur diese Episoden-Ordner)
Exit-Code 1 bei Fehlern; Warnungen brechen nicht ab.
"""
import ast
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from render.figuren import KINDS  # noqa: E402  (rein, ohne Seiteneffekte)

SZENEN = {"intro", "tag", "banner", "action", "point", "win", "tease", "cta", "guest", "table"}
TAGS = re.compile(r"\[(excited|laughs|dramatic|shouting|whispering|pause|sighs)\]\s*")
fehler, warnungen = [], []


def aktionen():
    """Namen aus ACTIONS = {...} in engine.py lesen, ohne die Engine auszuführen."""
    baum = ast.parse(open(os.path.join(ROOT, "engine.py"), encoding="utf-8").read())
    for knoten in baum.body:
        if isinstance(knoten, ast.Assign) and any(getattr(t, "id", "") == "ACTIONS" for t in knoten.targets):
            return {k.value for k in knoten.value.keys}
    return set()


SPRECHER = set(json.load(open(os.path.join(ROOT, "stimmen.json"), encoding="utf-8"))["stimmen"])
PREFIX = re.compile(r"^\s*(" + "|".join(map(re.escape, SPRECHER)) + r")\s*:\s*", re.M)


def norm(text):
    text = PREFIX.sub("", text)
    text = TAGS.sub("", text).replace("[laugh]", "")
    return re.sub(r"\s+", " ", re.sub(r"[^\wäöüÄÖÜß]+", " ", text.lower())).strip()


def dauer(pfad):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", pfad],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def episode(ordner, ACTIONS):
    name = os.path.basename(ordner)
    m = re.match(r"^F(\d+)_[a-z0-9_]+$|^S(\d+)_[a-z0-9_]+$", name)
    if not m:
        fehler.append(f"{name}: Ordnername muss FNN_slug oder SNN_slug sein (klein, ohne Umlaute)")
        return
    skript = os.path.join(ordner, "skript.txt")
    ep_pfad = os.path.join(ordner, "episode.json")
    if not os.path.exists(skript):
        fehler.append(f"{name}: skript.txt fehlt")
    if not os.path.exists(ep_pfad):
        (warnungen if name.startswith("F01_") else fehler).append(f"{name}: episode.json fehlt")
        return
    try:
        ep = json.load(open(ep_pfad, encoding="utf-8"))
    except json.JSONDecodeError as e:
        fehler.append(f"{name}: episode.json ist kein gültiges JSON ({e})")
        return
    if m.group(1) and ep.get("episode") != int(m.group(1)):
        fehler.append(f"{name}: 'episode' ist {ep.get('episode')}, Ordner sagt {int(m.group(1))}")
    f = ep.get("fighters", [])
    if len(f) != 2:
        fehler.append(f"{name}: genau 2 fighters nötig")
    arten = [x.get("kind") for x in f] + ([ep["guest"].get("kind")] if ep.get("guest") else [])
    for k in arten:
        if k not in KINDS:
            fehler.append(f"{name}: Figur '{k}' gibt es in render/figuren.py nicht")
    segs = ep.get("segments", [])
    if not segs:
        fehler.append(f"{name}: keine segments")
    for i, s in enumerate(segs):
        sc = s.get("scene")
        if sc not in SZENEN:
            fehler.append(f"{name}: Segment {i}: unbekannte Szene '{sc}'")
        if sc == "action" and s.get("type") not in ACTIONS:
            fehler.append(f"{name}: Segment {i}: unbekannte Aktion '{s.get('type')}'")
        if sc in ("point", "win") and s.get("side") not in (0, 1):
            fehler.append(f"{name}: Segment {i}: side muss 0 oder 1 sein")
        sp = s.get("speaker")
        if sp is not None and sp not in SPRECHER:
            fehler.append(f"{name}: Segment {i}: Sprecher '{sp}' fehlt in stimmen.json")
        if not s.get("text", "").strip():
            fehler.append(f"{name}: Segment {i}: text fehlt")
        if "[" in s.get("text", "").replace("[laugh]", ""):
            fehler.append(f"{name}: Segment {i}: Stimmen-Tag im text (nur im skript.txt erlaubt)")
    if not any(s.get("scene") == "win" for s in segs):
        fehler.append(f"{name}: keine win-Szene")
    if os.path.exists(skript) and segs:
        a = norm(open(skript, encoding="utf-8").read())
        b = norm(" ".join(s.get("text", "") for s in segs))
        if a != b:
            (warnungen if (m.group(1) and int(m.group(1)) < 10) else fehler).append(
                f"{name}: text-Felder weichen vom skript.txt ab (Untertitel passen sonst nicht zur Stimme)")
    stimme = os.path.join(ordner, "stimme.mp3")
    if os.path.exists(stimme):
        gesamt = dauer(stimme) + ep.get("tail", 2.4)
        if gesamt >= 60:
            fehler.append(f"{name}: Video wäre {gesamt:.1f} s lang (muss < 60 s sein)")


def liga():
    try:
        d = json.load(open(os.path.join(ROOT, "liga.json"), encoding="utf-8"))
    except json.JSONDecodeError as e:
        fehler.append(f"liga.json ist kein gültiges JSON ({e})")
        return
    chars = d.get("charaktere", {})
    kurz = {v.get("short"): k for k, v in chars.items()}
    for k, v in chars.items():
        if v.get("kind") not in KINDS:
            warnungen.append(f"liga.json: {k} hat Figur '{v.get('kind')}', die render/figuren.py nicht kennt")
    ids = [f.get("youtube") for f in d.get("folgen", []) if f.get("youtube")]
    if len(ids) != len(set(ids)):
        fehler.append("liga.json: eine YouTube-ID steht doppelt in 'folgen'")
    for f in d.get("folgen", []):
        if f.get("sieger") and f["sieger"] not in kurz:
            warnungen.append(f"liga.json: Folge {f.get('nr')}: Sieger '{f['sieger']}' ist kein bekannter Kurzname")
    siege = sum(v.get("siege", 0) for v in chars.values())
    nieder = sum(v.get("niederlagen", 0) for v in chars.values())
    if siege != nieder:
        warnungen.append(f"liga.json: Summe Siege ({siege}) ≠ Summe Niederlagen ({nieder})")
    nrs = [f["nr"] for f in d.get("folgen", []) if isinstance(f.get("nr"), int)]
    nxt = [n.get("folge") for n in d.get("naechste", [])]
    if nrs and nxt and min(nxt) <= max(nrs):
        fehler.append(f"liga.json: 'naechste' enthält Folge {min(nxt)}, die schon in 'folgen' steht")
    if nxt != sorted(nxt):
        warnungen.append("liga.json: 'naechste' ist nicht nach Folgennummer sortiert")


def main():
    ACTIONS = aktionen()
    nur = set(sys.argv[1:])
    basis = os.path.join(ROOT, "episodes")
    for name in sorted(os.listdir(basis)):
        pfad = os.path.join(basis, name)
        if os.path.isdir(pfad) and (not nur or name in nur):
            episode(pfad, ACTIONS)
        elif os.path.isfile(pfad):
            fehler.append(f"episodes/{name}: Dateien gehören in einen Episoden-Ordner")
    liga()
    for w in warnungen:
        print("WARNUNG:", w)
    for f in fehler:
        print("FEHLER: ", f)
    print(f"{len(fehler)} Fehler, {len(warnungen)} Warnungen")
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
