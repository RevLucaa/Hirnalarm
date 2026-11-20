#!/usr/bin/env python3
"""Wochenbericht aus den kostenlosen YouTube-Daten: beste Folgen, Disziplinen-Vergleich, Zuwachs, Kommentarwünsche.

Aufruf: python3 tools/wochenbericht.py            → schreibt berichte/<Jahr>-KW<NN>.md und gibt den Pfad aus
Quellen: statistik.json, verlauf.csv, kommentare.json (Branch „daten“ bzw. ./daten) und liga.json – alles kostenlos.
Der Bericht landet unter berichte/ im Daten-Ordner.
"""
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATEN = os.environ.get("DATEN_DIR") or os.path.join(ROOT, "daten")  # Branch „daten“ (Actions) bzw. ./daten lokal


def lade(pfad, standard):
    p = os.path.join(DATEN, pfad) if not pfad.endswith("liga.json") else os.path.join(ROOT, pfad)
    if not os.path.exists(p):
        return standard
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    jetzt = datetime.now(timezone.utc)
    vor7 = jetzt - timedelta(days=7)
    stat = lade("statistik.json", {"videos": [], "kanal": {}})
    komm = lade("kommentare.json", {"kommentare": []})
    liga = lade("liga.json", {"folgen": []})
    videos = stat["videos"]
    arena = {f.get("youtube"): f.get("arena", "ring") for f in liga.get("folgen", [])}
    nr = {f.get("youtube"): f.get("nr") for f in liga.get("folgen", [])}

    # Zuwachs der letzten 7 Tage aus dem Verlauf (ältester Stand ≥ 7 Tage zurück, sonst ältester vorhandener)
    alt = {}
    verlauf = os.path.join(DATEN, "verlauf.csv")
    if os.path.exists(verlauf):
        zeilen = list(csv.DictReader(open(verlauf, encoding="utf-8")))
        for z in sorted(zeilen, key=lambda z: z["stand"]):
            ts = datetime.fromisoformat(z["stand"])
            if z["video"] not in alt or ts <= vor7:
                alt[z["video"]] = int(z["aufrufe"])
    for v in videos:
        v["zuwachs"] = v["aufrufe"] - alt.get(v["id"], 0)
        v["arena"] = arena.get(v["id"], "ring")

    kw = jetzt.isocalendar()
    titel = f"Wochenbericht Hirnalarm {kw[0]}-KW{kw[1]:02d}"
    L = [f"# {titel}", "", f"Stand: {stat.get('stand', '–')} · Abonnenten: {stat.get('kanal', {}).get('subscriberCount', '–')} · "
         f"Aufrufe gesamt: {stat.get('kanal', {}).get('viewCount', '–')}", ""]

    L += ["## Beste Folgen (Aufrufe in den letzten 7 Tagen)", "", "| Folge | Titel | +Aufrufe | gesamt | Likes | Kommentare |", "|---|---|---|---|---|---|"]
    for v in sorted(videos, key=lambda v: -v["zuwachs"])[:5]:
        L.append(f"| {nr.get(v['id'], '–')} | [{v['titel'][:55]}](https://youtube.com/shorts/{v['id']}) | {v['zuwachs']} | "
                 f"{v['aufrufe']} | {v['likes']} | {v['kommentare']} |")

    L += ["", "## Ring vs. Rennen vs. Fußball (Durchschnitt pro Folge)", "", "| Disziplin | Folgen | Ø Aufrufe | Ø Likes | Ø Kommentare |", "|---|---|---|---|---|"]
    g = defaultdict(list)
    for v in videos:
        g[v["arena"]].append(v)
    for a, vs in sorted(g.items()):
        n = len(vs)
        L.append(f"| {a} | {n} | {sum(v['aufrufe'] for v in vs) // n} | {sum(v['likes'] for v in vs) / n:.1f} | "
                 f"{sum(v['kommentare'] for v in vs) / n:.1f} |")

    neue = [k for k in komm.get("kommentare", []) if k.get("datum") and datetime.fromisoformat(k["datum"].replace("Z", "+00:00")) >= vor7]
    L += ["", f"## Neue Kommentare ({len(neue)})", ""]
    for k in sorted(neue, key=lambda k: -k.get("likes", 0))[:15]:
        L.append(f"- **{k.get('autor')}** zu *{(k.get('video_titel') or '')[:40]}*: {k.get('text', '')[:140]}")
    if not neue:
        L.append("- keine")

    L += ["", "_Automatisch erstellt aus der YouTube Data API – kostet keine vidIQ-Credits._", ""]
    os.makedirs(os.path.join(DATEN, "berichte"), exist_ok=True)
    ziel = os.path.join(DATEN, "berichte", f"{kw[0]}-KW{kw[1]:02d}.md")
    with open(ziel, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(ziel)


if __name__ == "__main__":
    main()
