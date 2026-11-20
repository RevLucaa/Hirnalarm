# Hirnalarm 🍌🥊🍉

Deutsche 2D-„Brainrot“-Shorts: Obst-Figuren tragen eine fortlaufende Liga aus – im Wrestling-Ring, auf der Rennbahn und beim Fußball.
Zwei Folgen pro Tag (13:00 und 17:30) auf YouTube und Instagram, erstellt von Claude, gerendert mit Python.

| Kanal | Link |
|---|---|
| YouTube | [Hirnalarm](https://www.youtube.com/channel/UCmLDHEd4GKLvHuW58FarfCQ) |
| Instagram | @hirnalarm |

## So entsteht eine Folge

```
liga.json (Warteschlange)  →  skript.txt  →  stimme.mp3 (ElevenLabs)  →  episode.json
        →  Push  →  GitHub Action „Prüfen“ + „Video rendern“  →  Release FNN (Video + Vorschau)
        →  vidIQ: Upload & Einplanen (YouTube + Instagram)  →  liga.json aktualisieren
```

Der genaue Ablauf für Claude steht in [`CLAUDE.md`](CLAUDE.md) – ganz oben die **Grundregeln**, die immer gelten
(keine vidIQ-Credits, max. 2.000 ElevenLabs-Credits pro Folge, ElevenLabs nur für Stimmen, Rendern nur in GitHub Actions).

## Ordner

| Pfad | Inhalt |
|---|---|
| `engine.py` | Renderer: Timing, Szenen, Aktionen, Untertitel, Video-Ausgabe |
| `render/figuren.py` | alle Obst-Figuren, Gesichter, Requisiten, Easing |
| `render/ton.py` | Soundeffekte, Publikum und Beat |
| `render/aktionen.py` | alle Aktionen (Schlag, Wurf, Rennen …) |
| `render/kulissen.py` | Hintergründe und Arenen |
| `episodes/FNN_slug/` | eine Folge: `skript.txt`, `episode.json`, `stimme.mp3` |
| `stimmen.json` | feste Stimmen-Besetzung (Erzähler + jede Figur, ElevenLabs) |
| `tools/stimme_bauen.py` | Skript in Sprecher-Blöcke zerlegen, Teile zu `stimme.mp3` zusammenfügen |
| `liga.json` | Figuren mit Bilanz, bisherige Folgen, Warteschlange `naechste`, Themen-Pool |
| Branch `daten` | Kommentare, Aufrufzahlen, Verlauf und Wochenberichte (automatisch, YouTube Data API) |
| `tools/pruefen.py` | prüft Episoden und Liga auf Fehler |
| `tools/youtube_daten.py` | holt Kommentare und Aufrufe |
| `tools/bildtest.py` | vergleicht Demo-Bilder mit `tests/referenz/` |
| `tests/demo_stimmen/` | Demo-Folge für Tests |
| `tools/testton.py` | künstliche Test-Stimme für Probe-Renders |
| `fonts/` | Poppins Bold (SIL Open Font License) |

## Lokal testen (nur Vorschau – fertige Videos entstehen ausschließlich in GitHub Actions)

```bash
pip install -r requirements.txt          # dazu ffmpeg
python3 tools/pruefen.py                  # alles prüfen
python3 engine.py episodes/F09_zitrone_vs_erdbeere/episode.json stimme.mp3 F09.mp4
python3 engine.py <episode.json> <stimme.mp3> x.mp4 preview 5,20,40   # nur Einzelbilder (prev_*.png)
```

## GitHub Actions

| Workflow | Wann | Was |
|---|---|---|
| **Prüfen** | jeder Push | Episoden + Liga prüfen, Code-Check, jede Folge probeweise rendern, Bild-Test |
| **Video rendern** | Push einer `stimme.mp3`/`episode.json` oder manuell | rendert, speichert als Release `FNN` mit Video und Vorschau-Kontaktbogen |
| **Wochenbericht** | sonntags 19:00 | Bericht als Issue + `berichte/` (beste Folgen, Disziplinen, Kommentare) |
| **YouTube-Daten holen** | alle 6 h oder manuell | schreibt auf Branch `daten` (Secret `YT_API_KEY`) |
| **Repo einrichten** | manuell | legt Labels an |

Fertige Videos: `https://github.com/RevLucaa/Hirnalarm/releases/download/FNN/FNN.mp4`

## Die Liga

Figuren, Bilanz und Storyline stehen in [`liga.json`](liga.json). Zuschauer-Ideen aus den Kommentaren werden aufgegriffen
(z. B. Birken-Baum Rudi und Kiwi-Kevin).

## Ideen einwerfen

Neues Issue → Vorlage **Idee** oder **Zuschauerwunsch**. Der tägliche Lauf liest offene Issues mit diesen Labels und plant Passendes ein.

## Versionen

Änderungen am Renderer stehen in [`CHANGELOG.md`](CHANGELOG.md); die Version (`render/__init__.py`) steht in jedem Release.

## Lizenz

Alle Rechte vorbehalten – siehe [`LICENSE`](LICENSE).
