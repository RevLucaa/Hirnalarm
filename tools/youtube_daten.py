#!/usr/bin/env python3
"""Holt kostenlos (YouTube Data API v3, API-Schlüssel) Kommentare und Aufrufzahlen
des Hirnalarm-Kanals und schreibt sie nach daten/kommentare.json und daten/statistik.json.

Aufruf: YT_API_KEY=... python3 tools/youtube_daten.py
Kosten im API-Kontingent (10.000 Einheiten/Tag gratis): ca. 5–10 Einheiten pro Lauf.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CHANNEL_ID = "UCmLDHEd4GKLvHuW58FarfCQ"
API = "https://www.googleapis.com/youtube/v3/"
# Zielordner: in GitHub Actions der ausgecheckte Branch „daten“ (DATEN_DIR), lokal ./daten
OUT = os.environ.get("DATEN_DIR") or os.path.join(os.path.dirname(__file__), "..", "daten")


def get(endpoint, **params):
    params["key"] = os.environ["YT_API_KEY"]
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"Fehler {e.code} bei {endpoint}: {e.read().decode()[:500]}", file=sys.stderr)
        raise


def uploads():
    ch = get("channels", part="contentDetails,statistics", id=CHANNEL_ID)["items"][0]
    playlist = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while True:
        p = {"part": "contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            p["pageToken"] = token
        page = get("playlistItems", **p)
        ids += [i["contentDetails"]["videoId"] for i in page["items"]]
        token = page.get("nextPageToken")
        if not token or len(ids) >= 200:
            return ch["statistics"], ids


def statistik(ids):
    videos = []
    for i in range(0, len(ids), 50):
        page = get("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
        for v in page["items"]:
            s = v["statistics"]
            videos.append({
                "id": v["id"],
                "titel": v["snippet"]["title"],
                "veroeffentlicht": v["snippet"]["publishedAt"],
                "dauer": v["contentDetails"]["duration"],
                "aufrufe": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "kommentare": int(s.get("commentCount", 0)),
            })
    return sorted(videos, key=lambda v: v["veroeffentlicht"], reverse=True)


def kommentare(titel):
    threads, token = [], None
    while len(threads) < 300:
        p = {"part": "snippet,replies", "allThreadsRelatedToChannelId": CHANNEL_ID,
             "maxResults": 100, "order": "time", "textFormat": "plainText"}
        if token:
            p["pageToken"] = token
        page = get("commentThreads", **p)
        for t in page["items"]:
            top = t["snippet"]["topLevelComment"]["snippet"]
            vid = t["snippet"].get("videoId")
            threads.append({
                "video": vid,
                "video_titel": titel.get(vid),
                "autor": top.get("authorDisplayName"),
                "text": top.get("textDisplay"),
                "likes": top.get("likeCount", 0),
                "datum": top.get("publishedAt"),
                "antworten": [
                    {"autor": r["snippet"].get("authorDisplayName"), "text": r["snippet"].get("textDisplay")}
                    for r in t.get("replies", {}).get("comments", [])
                ],
            })
        token = page.get("nextPageToken")
        if not token:
            break
    return threads


def main():
    os.makedirs(OUT, exist_ok=True)
    stand = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kanal, ids = uploads()
    videos = statistik(ids)
    titel = {v["id"]: v["titel"] for v in videos}
    try:
        komm = kommentare(titel)
    except urllib.error.HTTPError:
        komm = None  # z. B. Kommentare deaktiviert – Statistik trotzdem speichern
    with open(os.path.join(OUT, "statistik.json"), "w", encoding="utf-8") as f:
        json.dump({"stand": stand, "kanal": kanal, "videos": videos}, f, ensure_ascii=False, indent=1)
    if komm is not None:
        with open(os.path.join(OUT, "kommentare.json"), "w", encoding="utf-8") as f:
            json.dump({"stand": stand, "anzahl": len(komm), "kommentare": komm}, f, ensure_ascii=False, indent=1)
    # Verlauf für Wochenvergleiche (eine Zeile pro Video und Abruf)
    verlauf = os.path.join(OUT, "verlauf.csv")
    neu = not os.path.exists(verlauf)
    with open(verlauf, "a", encoding="utf-8") as f:
        if neu:
            f.write("stand,video,aufrufe,likes,kommentare\n")
        for v in videos:
            f.write(f"{stand},{v['id']},{v['aufrufe']},{v['likes']},{v['kommentare']}\n")
    print(f"{len(videos)} Videos, {len(komm) if komm is not None else 'keine'} Kommentar-Threads")


if __name__ == "__main__":
    main()
