# Hirnalarm – täglicher Ablauf (für Claude)

YouTube-Kanal **Hirnalarm** (Channel-ID `UCmLDHEd4GKLvHuW58FarfCQ`): deutsche 2D-„Brainrot“-Shorts,
Obst-Duelle im Wrestling-Ring. **Zwei Videos pro Tag: 13:00 und 17:30 (Europe/Berlin), öffentlich.**
Luca hat den Ablauf freigegeben: Videos dürfen ohne Rückfrage erstellt und zu diesen Uhrzeiten öffentlich eingeplant werden.

## Dateien
- `engine.py` – Renderer: `python3 engine.py episode.json voice.mp3 out.mp4` (Vorschau: `... out.mp4 preview 5,20,40`)
- `liga.json` – Charaktere, Bilanz, bisherige Folgen, Warteschlange `naechste`
- `episodes/FNN_*.json|.txt` – Episoden-Definition und gesprochenes Skript

## Ablauf pro Lauf (bereitet die 2 Videos für MORGEN vor)
1. `liga.json` lesen. Die nächsten zwei Einträge aus `naechste` nehmen (Slot 13:00 und 17:30).
   Vorher mit `vidiq_user_videos` (Channel oben) prüfen, ob für morgen schon Videos eingeplant sind (`scheduledPublishAt`) – dann nichts doppelt machen.
2. **Skript** je Folge auf Deutsch schreiben: 740–830 Zeichen (≈ 120 Wörter, ≤ 850 ElevenLabs-Credits).
   Aufbau: Hook → Vorstellung Gegner → 2–3 Runden (`Runde eins: X!`) mit „Punkt für …!“ und Zwischenstand → `Finale!` → `NAME GEWINNT!` → Story-Teaser → „Schreib's in die Kommentare!“.
   Jede Folge braucht eine eigene Story und andere Aktionen/Gags (YouTube „inauthentic content“ – keine Kopien!). Bilanz/Storyline aus `liga.json` weiterführen.
   Tags erlaubt: `[excited]` am Anfang, `[laughs]`, `[dramatic]` vor Finale, `[shouting]` beim Sieger.
3. **Stimme** (ElevenLabs): `creative_generate_speech`, `model_id=eleven_v4`, `voice_id=VaRABgCVZ3ugJKxSuaMR` (WasMachtHarald),
   `generations_count=1`, `flow_id=hMLY5a8Lk2A1cOWhQmuf`. Danach `creative_get_generations` → `full_res_url` mit `curl` laden.
4. **Tempo**: Dauer messen; mit `ffmpeg -af atempo=X` auf ≈ 55–57 s bringen (X zwischen 0.88 und 1.0). In der Episode `tail` so setzen, dass Gesamtlänge ≈ 58–59,5 s (< 60 s!).
5. **Episode-JSON** schreiben (Muster: `episodes/F02_*.json`). Die `text`-Felder müssen das Skript **ohne** Tags exakt wiedergeben (an Satzzeichen . ! ? : getrennt).
   `[laugh]` im Text markiert ein Lachen. Szenen: `intro`, `tag` (side), `banner` (label, color), `action` (type, actor, Parameter), `point` (side, show_score), `win` (side), `tease` (teaser kind | loser_expr), `cta` (line1, line2, challenger kind).
   Aktionen: `race` (trip), `slam` (bounce, peel, jump0, hit), `post` (hit), `spin`, `headbutt`, `clash` (splash). Neue Aktionen/Charaktere gern in `engine.py` ergänzen.
   Charakter-Arten: banana, melon, pineapple, coconut, strawberry, lemon, cucumber. Fighter 0 = links, 1 = rechts. `episode` = Folgennummer.
6. **Vorschau** (`preview` mit ~12 Zeitpunkten), Bilder als Kontaktbogen ansehen, Timing der `hit`-Werte an die Phrasen-Zeiten (stderr) anpassen. Dann rendern.
7. **Ablage**: `gh release create FNN <video.mp4> --repo RevLucaa/hirnalarm --title "Folge NN" --notes "..."`;
   Asset-URL: `https://github.com/RevLucaa/hirnalarm/releases/download/FNN/<datei>.mp4`.
8. **Upload**: `vidiq_video_upload` mit `url` = Asset-URL → `uploadId`. `vidiq_social_post_draft_create` mit
   YouTube-Ziel `UCmLDHEd4GKLvHuW58FarfCQ`, `privacyStatus: public`, `categoryId: 23`, Titel `X vs. Y 🍌🍉 … #shorts`,
   Beschreibung mit „Folge NN“, Kommentar-Frage und Hashtags, ~10 Tags, `publishAt` = morgen 13:00 bzw. 17:30 `+01:00` (Sommerzeit `+02:00`).
   Dann `vidiq_social_post_publish`. Mit `vidiq_user_videos` prüfen, dass `scheduledPublishAt` stimmt.
9. `liga.json` aktualisieren (Bilanz, `folgen` inkl. YouTube-ID, `naechste` um 2 kürzen und neue Duelle hinten anhängen, gern Kommentarwünsche aus `vidiq_video_comments` der letzten Videos aufgreifen).
   Episoden-Dateien committen und pushen (`git -c push.negotiate=true push`).
10. Kurze Zusammenfassung an Luca: Titel, Uhrzeiten, YouTube-Links, verbrauchte ElevenLabs-Credits.

## Grenzen
- ElevenLabs: Starter-Plan 40.000 Credits/Monat. Vor dem Erzeugen `account_get_usage` prüfen; wenn < 2.000 übrig, abbrechen und Luca Bescheid geben.
- Nie öffentlich posten, wenn das Rendern/Prüfen fehlschlägt – lieber Lauf abbrechen und melden.
