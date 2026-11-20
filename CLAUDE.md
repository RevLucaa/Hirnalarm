# Hirnalarm – täglicher Ablauf (für Claude)

YouTube-Kanal **Hirnalarm** (Channel-ID `UCmLDHEd4GKLvHuW58FarfCQ`): deutsche 2D-„Brainrot“-Shorts,
Obst-Duelle im Wrestling-Ring. **Zwei Videos pro Tag: 13:00 und 17:30 (Europe/Berlin), öffentlich.**
Luca hat den Ablauf freigegeben: Videos dürfen ohne Rückfrage erstellt und zu diesen Uhrzeiten öffentlich eingeplant werden.

## Dateien
- `engine.py` – Renderer: `python3 engine.py episode.json stimme.mp3 out.mp4` (Vorschau: `... out.mp4 preview 5,20,40`)
- `render/figuren.py` – alle Figuren/Requisiten (neue Figur: `spr_<art>` + Eintrag in `KINDS`/`BASE_SC`); `render/ton.py` – Soundeffekte
- `liga.json` – Charaktere, Bilanz, bisherige Folgen, Warteschlange `naechste`
- `episodes/FNN_slug/` – je Folge ein Ordner: `skript.txt` (mit Stimmen-Tags), `episode.json`, `stimme.mp3` (Specials: `SNN_slug/`)
- `tools/pruefen.py` – prüft Episoden + Liga; **vor jedem Push ausführen**, muss „0 Fehler“ melden
- Übersicht für Menschen: `README.md`

## Ablauf pro Lauf (bereitet die 2 Videos für MORGEN vor)
1. `liga.json` lesen. Die nächsten zwei Einträge aus `naechste` nehmen (Slot 13:00 und 17:30).
   Vorher mit `vidiq_social_post_list` (kostenlos; `statuses: ["scheduled"]`, `platforms: ["YOUTUBE"]`) prüfen, ob für morgen schon Videos eingeplant sind – dann nichts doppelt machen.
2. **Skript** je Folge auf Deutsch schreiben: 740–830 Zeichen (≈ 120 Wörter, ≤ 850 ElevenLabs-Credits).
   Aufbau: Hook → Vorstellung Gegner → 2–3 Runden (`Runde eins: X!`) mit „Punkt für …!“ und Zwischenstand → `Finale!` → `NAME GEWINNT!` → Story-Teaser → „Schreib's in die Kommentare!“.
   Jede Folge braucht eine eigene Story und andere Aktionen/Gags (YouTube „inauthentic content“ – keine Kopien!). Bilanz/Storyline aus `liga.json` weiterführen.
   Tags erlaubt: `[excited]` am Anfang, `[laughs]`, `[dramatic]` vor Finale, `[shouting]` beim Sieger.
3. **Stimme** (ElevenLabs): `creative_generate_speech`, `model_id=eleven_v4`, `voice_id=VaRABgCVZ3ugJKxSuaMR` (WasMachtHarald),
   `generations_count=1`, `flow_id=hMLY5a8Lk2A1cOWhQmuf`. Danach `creative_get_generations` → `full_res_url` mit `curl` laden.
4. **Tempo**: Dauer messen; mit `ffmpeg -af atempo=X` auf ≈ 55–57 s bringen (X zwischen 0.88 und 1.0). In der Episode `tail` so setzen, dass Gesamtlänge ≈ 58–59,5 s (< 60 s!).
5. **Episode-JSON** schreiben als `episodes/FNN_slug/episode.json` (Muster: `episodes/F09_zitrone_vs_erdbeere/episode.json`); Skript als `skript.txt`, getempte Stimme als `stimme.mp3` in denselben Ordner. Die `text`-Felder müssen das Skript **ohne** Tags exakt wiedergeben (an Satzzeichen . ! ? : getrennt).
   `[laugh]` im Text markiert ein Lachen. Szenen: `intro`, `tag` (side), `banner` (label, color), `action` (type, actor, Parameter), `point` (side, show_score), `win` (side), `tease` (teaser kind | loser_expr), `cta` (line1, line2, challenger kind).
   Aktionen (siehe `ACTIONS` in `engine.py`): u. a. `race` (trip), `slam` (bounce, peel, jump0, hit), `post` (hit), `spin`, `headbutt`, `clash` (splash), `throw`, `bowl`, `catapult`. Neue Aktionen in `engine.py`, neue Figuren in `render/figuren.py` ergänzen.
   Charakter-Arten (siehe `KINDS` in `render/figuren.py`): banana, melon, pineapple, coconut, strawberry, lemon, cucumber, birch, kiwi. Fighter 0 = links, 1 = rechts. `episode` = Folgennummer.
6. **Vorschau** lokal (`preview` mit ~12 Zeitpunkten), Bilder als Kontaktbogen ansehen, Timing der `hit`-Werte an die Phrasen-Zeiten (stderr) anpassen.
   Dann `python3 tools/pruefen.py FNN_slug` → muss 0 Fehler melden.
7. **Rendern in GitHub** (Standard): Ordner committen und pushen (`git -c push.negotiate=true push`). Die Action „Video rendern“ startet automatisch,
   rendert und legt das Release `FNN` mit `FNN.mp4` und `FNN_vorschau.jpg` an. Status per REST abfragen (kein `gh run`/`gh release` – GraphQL ist gesperrt):
   `gh api "repos/RevLucaa/Hirnalarm/actions/runs?per_page=3" --jq '.workflow_runs[]|[.name,.status,.conclusion]|@tsv'` (dauert einige Minuten).
   Neu rendern: `gh api -X POST repos/RevLucaa/Hirnalarm/actions/workflows/rendern.yml/dispatches -f ref=main -f "inputs[folgen]=FNN_slug"`.
   Öffentliche URL: `https://github.com/RevLucaa/Hirnalarm/releases/download/FNN/FNN.mp4` (mit `curl -sIL` auf 200 prüfen); Vorschau-JPG genauso ansehen.
   **Notlösung**, falls die Action fehlschlägt: lokal rendern und über den Branch `ablage` bereitstellen (wird bei jedem Lauf überschrieben):
   ```
   rm -rf /tmp/ablage && mkdir /tmp/ablage && cd /tmp/ablage && git init -q -b ablage
   git remote add origin https://github.com/RevLucaa/hirnalarm
   cp <F_NN.mp4> FNN.mp4 && cp <F_MM.mp4> FMM.mp4 && git add . && git commit -qm "Ablage FNN FMM" && git push -f origin ablage
   ```
   Notlösungs-URL: `https://raw.githubusercontent.com/RevLucaa/hirnalarm/ablage/FNN.mp4` (vorher mit `curl -sI` auf 200 prüfen).
8. **Upload**: `vidiq_video_upload` mit `url` = Release-URL (bzw. Notlösungs-URL) → `uploadId`. `vidiq_social_post_draft_create` mit
   YouTube-Ziel `UCmLDHEd4GKLvHuW58FarfCQ`, `privacyStatus: public`, `categoryId: 23`, Titel `X vs. Y 🍌🍉 … #shorts`,
   Beschreibung mit „Folge NN“, Kommentar-Frage und Hashtags, ~10 Tags, `publishAt` = morgen 13:00 bzw. 17:30 `+01:00` (Sommerzeit `+02:00`).
   **Im selben Draft zusätzlich Instagram** als zweites Ziel: `platform: INSTAGRAM`, `platformAccountId: 29785569181129808` (@hirnalarm),
   eigener `text` (Titel-Zeile, 1–2 Sätze, Kommentar-Frage, Hashtags `#brainrot #obstkampf … #lustig #comedy #reels #deutsch`, ohne #shorts), gleiche `publishAt`.
   Dann `vidiq_social_post_publish` (alle Ziele). Mit `vidiq_social_post_status` (kostenlos) prüfen, dass YouTube und Instagram `scheduled` sind und die Uhrzeit stimmt.
   Hirnalarm-TikTok („BrainrotLab“) ist noch nicht mit vidIQ verbunden – sobald es in `vidiq_social_account_list` auftaucht, ebenfalls als Ziel aufnehmen
   (privacyLevel PUBLIC_TO_EVERYONE, allowComment true, musicUsageConfirmed true, isAiGenerated false).
9. `liga.json` aktualisieren (Bilanz, `folgen` inkl. YouTube-ID, `naechste` um 2 kürzen und neue Duelle hinten anhängen, gern Kommentarwünsche aus `daten/kommentare.json` aufgreifen – vorher `git pull`).
   `liga.json` committen und pushen (`git -c push.negotiate=true push`); die Action „Prüfen“ muss grün sein.
10. Kurze Zusammenfassung an Luca: Titel, Uhrzeiten, YouTube-Links, verbrauchte ElevenLabs-Credits.

## Weitere Sportarten: Rennen und Fußball (Wunsch von Luca, 19./20.11.2026 – ersetzt die Regel vom 17.11.)
Kämpfen im Ring bleibt der Kern. Dazu kommen **genau zwei** weitere Sportarten: **Wettrennen** (`"arena": "bahn"`) und **Fußball** (`"arena": "fussball"`, z. B. Elfmeterschießen).
Keine weiteren Sportarten/Themen aus `themen_pool`, bis die Auswertung (Punkt 4) es erlaubt.
1. **F10–F11: Ring.** Im Story-Teaser das erste Rennen andeuten (z. B. „Anton will es nicht mehr mit Fäusten klären – sondern auf der Bahn!“).
2. **F12: erstes Rennen** als Grudge-Match Bernd vs. Anton (Revanche für F02).
   Fußball gibt es schon: Special S1 (20.11.) Bernd vs. Kalle, Elfmeterschießen, Sieger Kalle.
3. **Ab F13: pro Tag eine Ring-Folge und eine Sport-Folge; die Sport-Folgen wechseln sich ab (Rennen, Fußball, Rennen, …).** Nie zweimal dieselbe Sportart hintereinander.
   Die Ergebnisse hängen zusammen (Verlierer eines Rennens/Spiels muss im Ring gegen den Champion ran, Revanchen in der anderen Disziplin usw.).
   Jede Folge endet mit einem Cliffhanger, der in eine andere Disziplin führt.
4. **Auswertung nach ca. F20:** Aufrufe/Likes/Kommentare aus `daten/statistik.json` (kostenlos) Ring vs. Rennen vs. Fußball vergleichen; Zuschauerdauer (`vidiq_channel_analytics`, 5 Credits) nur, wenn genug vidIQ-Credits da sind.
   Läuft eine Sportart deutlich schlechter als der Ring → nur noch als seltenes Special. Ergebnis kurz an Luca melden, erst danach über weitere Sportarten nachdenken.
Bilanz und Storyline gelten über alle Disziplinen. In `engine.py` fehlen beide Kulissen noch – beim ersten Bedarf ergänzen:
`bahn` (Laufbahn, Start/Ziel, Zuschauer; Aktionen Start, Überholen, Ausrutschen, Zielfoto; `race` als Basis) und
`fussball` (Tor, Rasen, Ball; Aktionen Schuss, Parade, Pfosten, Tor-Jubel; Look an Special S1 `7P963hZzTs0` anlehnen).
Sport-Skript: Hook → Grund für das Duell → 2–3 Abschnitte (Rennen: `Start!`, `Halbzeit!`, `Zielgerade!`; Fußball: `Schuss eins!` …) statt Runden → `NAME GEWINNT!` → Cliffhanger → Frage.
Jede Episode, die außerhalb dieses Ablaufs entsteht, ebenfalls in `liga.json` → `folgen` eintragen (Nummer `S<n>`).

## Hook und Drama (gilt für jede Folge, ab F10)
- **Erster Satz = Konflikt, mitten drin**, keine Vorstellung: „Kalle hat Mannis Gürtel geklaut. Heute holt er ihn zurück!“ statt „Neu in der Obst-Liga: …“. Grund des Duells kommt aus der Storyline (Revanche, Verrat, Schummelei).
- Folgenübergreifendes Drama: jede Folge greift ein offenes Ereignis der Vorfolgen auf und legt ein neues an (in `liga.json` → Charakter-`notiz` festhalten).
- Schluss: statt allgemein „Wer soll als Nächstes …?“ eine **konkrete Streitfrage**, die man nur im Kommentar beantworten kann (z. B. „Hat Anton geschummelt – ja oder nein?“). Die Frage im Video sprechen und als Text einblenden.

## Kostenlose Daten statt vidIQ-Credits
vidIQ-Credits sind knapp (150/Monat). Hochladen, Entwurf, Einplanen, `social_post_list` und `social_post_status` kosten 0 Credits und bleiben erlaubt.
**Nicht verwenden** (kosten Credits): `vidiq_user_videos`, `vidiq_video_comments`, `vidiq_get_videos_by_ids`, `vidiq_channel_analytics` (Ausnahme: Auswertung oben).
Kommentare und Aufrufzahlen holt stattdessen die GitHub Action `youtube-daten.yml` alle 6 Stunden über die YouTube Data API (Secret `YT_API_KEY`) nach
`daten/kommentare.json` und `daten/statistik.json`. Fehlen die Dateien oder sind sie älter als 2 Tage, Luca kurz Bescheid geben und ohne Kommentarwünsche weitermachen.

## Grenzen
- ElevenLabs: Starter-Plan 40.000 Credits/Monat. Vor dem Erzeugen `account_get_usage` prüfen; wenn < 2.000 übrig, abbrechen und Luca Bescheid geben.
- Nie öffentlich posten, wenn das Rendern/Prüfen fehlschlägt – lieber Lauf abbrechen und melden.
