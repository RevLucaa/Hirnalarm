# Hirnalarm – täglicher Ablauf (für Claude)

YouTube-Kanal **Hirnalarm** (Channel-ID `UCmLDHEd4GKLvHuW58FarfCQ`): deutsche 2D-„Brainrot“-Shorts,
Obst-Duelle im Wrestling-Ring. **Zwei Videos pro Tag: 13:00 und 17:30 (Europe/Berlin), öffentlich.**
Luca hat den Ablauf freigegeben: Videos dürfen ohne Rückfrage erstellt und zu diesen Uhrzeiten öffentlich eingeplant werden.

## ⚠️ Grundregeln – gelten immer und gehen allem anderen in dieser Datei vor
Festgelegt von Luca (20.11.2026). Steht irgendwo unten etwas anderes, gilt diese Liste. Kann eine Regel nicht eingehalten werden: Lauf abbrechen und Luca Bescheid geben.
1. **Keine vidIQ-Credits.** Nur Werkzeuge mit „Cost: 0 credit(s)“ verwenden (Upload, Entwurf, Einplanen, `social_post_list`, `social_post_status`, `social_account_list`).
   Alles, was Credits kostet (`user_videos`, `video_comments`, `channel_analytics`, `get_videos_by_ids`, `watch_*`, Suchen, `compose` …), ist verboten – auch für Auswertungen.
   Kommentare und Zahlen kommen vom Branch `daten` (YouTube Data API, kostenlos) – siehe „Kostenlose Daten“ unten.
2. **ElevenLabs: höchstens 2.000 Credits pro Folge – weniger ist besser.** Ziel ≈ 800–1.000. Vor dem Erzeugen mit `tools/stimme_bauen.py bloecke` rechnen;
   jeder Block wird genau einmal erzeugt, Neuversuche zählen mit. Lieber Skript kürzen als die Grenze ausreizen.
3. **ElevenLabs nur für Stimmen.** Keine Bilder, Videos, Musik, Soundeffekte oder Flows zum Rendern über ElevenLabs.
4. **Immer in der Cloud rendern.** Das fertige Video entsteht ausschließlich über die GitHub Action „Video rendern“ (Release `FNN`).
   Lokal nur Vorschau-Einzelbilder (`preview`). Schlägt die Action fehl: einmal neu starten; klappt es dann nicht, abbrechen und melden – nichts lokal Gerendertes posten.
5. **Nie posten, wenn etwas fehlschlägt.** `tools/pruefen.py` muss 0 Fehler melden, die Action „Prüfen“ grün sein und das Vorschau-JPG angesehen werden.
6. **Nichts doppelt einplanen.** Vor jedem Lauf mit `vidiq_social_post_list` prüfen, was schon geplant ist. Eingeplante Posts nicht verändern.
7. **Jede Folge ist neu.** Eigene Story, eigene Gags, keine Kopien alter Skripte (YouTube „inauthentic content“). Bilanz und Storyline in `liga.json` pflegen.
8. **Keine Geheimnisse ins Repo oder in den Chat.** API-Schlüssel nur als GitHub-Secret.
9. **Am Ende immer kurz an Luca berichten:** Titel, Uhrzeiten, Links, verbrauchte ElevenLabs-Credits (pro Folge).

## Dateien
- `engine.py` – Renderer: `python3 engine.py episode.json stimme.mp3 out.mp4` (Vorschau: `... out.mp4 preview 5,20,40`)
- `render/figuren.py` – alle Figuren/Requisiten (neue Figur: `spr_<art>` + Eintrag in `KINDS`/`BASE_SC`); `render/ton.py` – Soundeffekte
- `liga.json` – Charaktere, Bilanz, bisherige Folgen, Warteschlange `naechste`
- `stimmen.json` – feste Stimmen-Besetzung (Erzähler + jede Figur, voice_id, Credit-Faktor); `tools/stimme_bauen.py` – Sprecher-Blöcke + Zusammenfügen
- `episodes/FNN_slug/` – je Folge ein Ordner: `skript.txt` (mit Stimmen-Tags), `episode.json`, `stimme.mp3` (Specials: `SNN_slug/`)
- `tools/wochenbericht.py` + Action „Wochenbericht“ – jeden Sonntag 19:00 Bericht als Issue (E-Mail an Luca), kostenlos aus dem Branch `daten`
- `tests/demo_stimmen/` – Demo-Folge zum Testen von Renderer-Änderungen (Cloud-Test: `rendern.yml` mit `test=true` → Vorab-Release `test`, wird überschrieben, nie posten)
- `render/aktionen.py` – Aktionen (Schlag, Wurf, Rennen …), `render/kulissen.py` – Hintergründe/Arenen (neue Arenen hier), `render/__init__.py` – `VERSION`
- `tools/bildtest.py` + `tests/referenz/` – Bild-Test gegen Referenzbilder (läuft in „Prüfen“)
- `tools/pruefen.py` – prüft Episoden + Liga; **vor jedem Push ausführen**, muss „0 Fehler“ melden
- Übersicht für Menschen: `README.md`

## Ablauf pro Lauf (bereitet die 2 Videos für MORGEN vor)
1. `liga.json` lesen. Die nächsten zwei Einträge aus `naechste` nehmen (Slot 13:00 und 17:30).
   Vorher mit `vidiq_social_post_list` (kostenlos; `statuses: ["scheduled"]`, `platforms: ["YOUTUBE"]`) prüfen, ob für morgen schon Videos eingeplant sind – dann nichts doppelt machen.
2. **Skript** je Folge auf Deutsch schreiben: 740–830 Zeichen (≈ 120 Wörter). **Mit Figurenstimmen** (ab F10): eine Zeile pro Wortbeitrag im Format
   `Sprecher: Text` (Sprecher = Kurzname aus `stimmen.json` oder `Erzähler`). Der Erzähler trägt die Folge (Runden, Punkte, Sieger),
   die zwei Kämpfer haben je 2–4 kurze Sätze (Sprüche, Drohungen, Reaktionen – max. ~12 Wörter pro Satz), Gäste/Schiri gelegentlich einen.
   Aufbau: Hook → Vorstellung Gegner → 2–3 Runden (`Runde eins: X!`) mit „Punkt für …!“ und Zwischenstand → `Finale!` → `NAME GEWINNT!` → Story-Teaser → „Schreib's in die Kommentare!“.
   Jede Folge braucht eine eigene Story und andere Aktionen/Gags (YouTube „inauthentic content“ – keine Kopien!). Bilanz/Storyline aus `liga.json` weiterführen.
   Tags erlaubt: `[excited]` am Anfang, `[laughs]`, `[dramatic]` vor Finale, `[shouting]` beim Sieger.
3. **Stimmen** (ElevenLabs): `python3 tools/stimme_bauen.py bloecke episodes/FNN_slug` → Liste der Sprecher-Blöcke mit voice_id und Credits
   (Exit 1 über 2.000 → Skript kürzen). Pro Block **genau einmal** `creative_generate_speech` (`model_id=eleven_v4`, voice_id aus der Liste,
   `generations_count=1`, `flow_id=hMLY5a8Lk2A1cOWhQmuf`; alle Blöcke einer Folge parallel starten). Dann `creative_get_generations` → `full_res_url`
   mit `curl` als `episodes/FNN_slug/teile/01.mp3`, `02.mp3` … (Reihenfolge = Block-Nr.) laden. Klingt ein Block falsch (Aussprache, Betonung),
   nur diesen einen Block neu erzeugen – Credits mitzählen, Summe ≤ 2.000.
4. **Zusammenfügen + Tempo**: `python3 tools/stimme_bauen.py zusammenfuegen episodes/FNN_slug` – gleicht die Lautstärke aller Stimmen an,
   setzt kurze Pausen zwischen Sprechern und bringt das Ganze auf ≈ 55–57 s → `stimme.mp3`. In der Episode `tail` so setzen, dass Gesamtlänge ≈ 58–59,5 s (< 60 s!).
5. **Episode-JSON** schreiben als `episodes/FNN_slug/episode.json` (Muster: `episodes/F09_zitrone_vs_erdbeere/episode.json`); Skript als `skript.txt`, getempte Stimme als `stimme.mp3` in denselben Ordner. Die `text`-Felder müssen das Skript **ohne** Tags exakt wiedergeben (an Satzzeichen . ! ? : getrennt).
   Segmente, die eine Figur spricht, bekommen `"speaker": "<Kurzname>"` (zeigt ein Namensschild in Figurenfarbe über dem Untertitel); Erzähler-Segmente ohne `speaker`.
   Segmentgrenzen müssen an Sprecherwechseln liegen (ein Segment = ein Sprecher). `[laugh]` im Text markiert ein Lachen. Szenen: `intro`, `tag` (side), `banner` (label, color), `action` (type, actor, Parameter), `point` (side, show_score), `win` (side), `tease` (teaser kind | loser_expr), `cta` (line1, line2, challenger kind).
   Aktionen (siehe `ACTIONS` in `render/aktionen.py`): u. a. `race` (trip), `slam` (bounce, peel, jump0, hit), `post` (hit), `spin`, `headbutt`, `clash` (splash), `throw`, `bowl`, `catapult`. Neue Aktionen in `render/aktionen.py`, neue Figuren in `render/figuren.py` ergänzen.
   Charakter-Arten (siehe `KINDS` in `render/figuren.py`): banana, melon, pineapple, coconut, strawberry, lemon, cucumber, birch, kiwi, cat, apple. Fighter 0 = links, 1 = rechts. `episode` = Folgennummer.
6. **Vorschau** lokal (`preview` mit ~12 Zeitpunkten), Bilder als Kontaktbogen ansehen, Timing der `hit`-Werte an die Phrasen-Zeiten (stderr) anpassen.
   Dann `python3 tools/pruefen.py FNN_slug` → muss 0 Fehler melden.
7. **Rendern in GitHub** (Standard): Ordner committen und pushen (`git -c push.negotiate=true push`). Die Action „Video rendern“ startet automatisch,
   rendert und legt das Release `FNN` mit `FNN.mp4` und `FNN_vorschau.jpg` an. Status per REST abfragen (kein `gh run`/`gh release` – GraphQL ist gesperrt):
   `gh api "repos/RevLucaa/Hirnalarm/actions/runs?per_page=3" --jq '.workflow_runs[]|[.name,.status,.conclusion]|@tsv'` (dauert einige Minuten).
   Neu rendern: `gh api -X POST repos/RevLucaa/Hirnalarm/actions/workflows/rendern.yml/dispatches -f ref=main -f "inputs[folgen]=FNN_slug"`.
   Öffentliche URL: `https://github.com/RevLucaa/Hirnalarm/releases/download/FNN/FNN.mp4` (prüfen mit `curl -sL -r 0-0 -o /dev/null -w '%{http_code}' URL` → 206 oder 200; `curl -I` meldet fälschlich 401). Vorschau-JPG `…/FNN/FNN_vorschau.jpg` herunterladen und ansehen.
   Schlägt die Action fehl: Log lesen, Ursache beheben, einmal neu starten. Klappt es dann nicht → abbrechen und Luca melden (Grundregel 4). Kein lokales Rendern als Ersatz.
8. **Upload**: `vidiq_video_upload` mit `url` = Release-URL → `uploadId`. `vidiq_social_post_draft_create` mit
   YouTube-Ziel `UCmLDHEd4GKLvHuW58FarfCQ`, `privacyStatus: public`, `categoryId: 23`, Titel `X vs. Y 🍌🍉 … #shorts`,
   Beschreibung mit „Folge NN“, Kommentar-Frage und Hashtags, ~10 Tags, `publishAt` = morgen 13:00 bzw. 17:30 `+01:00` (Sommerzeit `+02:00`).
   **Im selben Draft zusätzlich Instagram** als zweites Ziel: `platform: INSTAGRAM`, `platformAccountId: 29785569181129808` (@hirnalarm),
   eigener `text` (Titel-Zeile, 1–2 Sätze, Kommentar-Frage, Hashtags `#brainrot #obstkampf … #lustig #comedy #reels #deutsch`, ohne #shorts), gleiche `publishAt`.
   Dann `vidiq_social_post_publish` (alle Ziele). Mit `vidiq_social_post_status` (kostenlos) prüfen, dass YouTube und Instagram `scheduled` sind und die Uhrzeit stimmt.
   Hirnalarm-TikTok („BrainrotLab“) ist noch nicht mit vidIQ verbunden – sobald es in `vidiq_social_account_list` auftaucht, ebenfalls als Ziel aufnehmen
   (privacyLevel PUBLIC_TO_EVERYONE, allowComment true, musicUsageConfirmed true, isAiGenerated false).
9. `liga.json` aktualisieren (Bilanz, `folgen` inkl. YouTube-ID, `naechste` um 2 kürzen und neue Duelle hinten anhängen, gern Kommentarwünsche aus `kommentare.json` (Branch `daten`) und offene Issues mit Label `idee`/`zuschauerwunsch` aufgreifen – vorher `git pull`).
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
4. **Auswertung nach ca. F20:** Aufrufe/Likes/Kommentare aus `statistik.json` bzw. dem Wochenbericht (Branch `daten`, kostenlos) Ring vs. Rennen vs. Fußball vergleichen. Keine vidIQ-Analytics (Grundregel 1).
   Läuft eine Sportart deutlich schlechter als der Ring → nur noch als seltenes Special. Ergebnis kurz an Luca melden, erst danach über weitere Sportarten nachdenken.
Bilanz und Storyline gelten über alle Disziplinen. In `render/kulissen.py` fehlen beide Kulissen noch – beim ersten Bedarf ergänzen (Aktionen in `render/aktionen.py`):
`bahn` (Laufbahn, Start/Ziel, Zuschauer; Aktionen Start, Überholen, Ausrutschen, Zielfoto; `race` als Basis) und
`fussball` (Tor, Rasen, Ball; Aktionen Schuss, Parade, Pfosten, Tor-Jubel; Look an Special S1 `7P963hZzTs0` anlehnen).
Sport-Skript: Hook → Grund für das Duell → 2–3 Abschnitte (Rennen: `Start!`, `Halbzeit!`, `Zielgerade!`; Fußball: `Schuss eins!` …) statt Runden → `NAME GEWINNT!` → Cliffhanger → Frage.
Jede Episode, die außerhalb dieses Ablaufs entsteht, ebenfalls in `liga.json` → `folgen` eintragen (Nummer `S<n>`).

## Staffel 1 – Der Obst-Liga-Pokal (Plan von Luca, 20.11.2026)
Der Bogen bis F30 steht in `liga.json` → `staffel_1` (Punkte, Halbfinale F27–28, Finale F30). Jede neue Folge und jeder neue Eintrag in `naechste`
muss in diesen Bogen passen. **Qualitätsmaßstab ist F11** (`episodes/F11_ananas_vs_melone_titelkampf/skript.txt`): Konflikt im ersten Satz,
kurze Figurensätze, ein Schummel-/Story-Gag, konkrete Streitfrage, Loop-Ende – plus alles aus „Hook und Drama“.

## Hook und Drama (gilt für jede Folge, ab F10)
- **Erster Satz = Konflikt, mitten drin**, keine Vorstellung: „Kalle hat Mannis Gürtel geklaut. Heute holt er ihn zurück!“ statt „Neu in der Obst-Liga: …“. Grund des Duells kommt aus der Storyline (Revanche, Verrat, Schummelei).
- Folgenübergreifendes Drama: jede Folge greift ein offenes Ereignis der Vorfolgen auf und legt ein neues an (in `liga.json` → Charakter-`notiz` festhalten).
- **Loop-Ende:** Der letzte gesprochene Satz endet so, dass er nahtlos in den ersten Satz der Folge übergeht (z. B. Ende: „Wisst ihr, was ich jetzt mache?“ → Anfang: „Skandal! Kalle hat Mannis Gürtel geklaut!“). Kurzer `tail` (≈ 1–2 s), damit der Übergang sitzt.
- **Erstes Bild = Action:** In den ersten 0,5 s ist schon etwas los (Figur mitten in der Bewegung, Schlag, Grimasse) – kein ruhiges Standbild.
- Mundbewegung, Namensschild, Publikum und Soundeffekte macht der Renderer automatisch, sobald Segmente ein `speaker`-Feld haben.
- Schluss: statt allgemein „Wer soll als Nächstes …?“ eine **konkrete Streitfrage**, die man nur im Kommentar beantworten kann (z. B. „Hat Anton geschummelt – ja oder nein?“). Die Frage im Video sprechen und als Text einblenden.

## Kostenlose Daten statt vidIQ-Credits
vidIQ-Credits sind knapp (150/Monat). Hochladen, Entwurf, Einplanen, `social_post_list` und `social_post_status` kosten 0 Credits und bleiben erlaubt.
**Nicht verwenden** (kosten Credits, siehe Grundregel 1): `vidiq_user_videos`, `vidiq_video_comments`, `vidiq_get_videos_by_ids`, `vidiq_channel_analytics` – ohne Ausnahme.
Kommentare und Aufrufzahlen holt stattdessen die GitHub Action `youtube-daten.yml` alle 6 Stunden über die YouTube Data API (Secret `YT_API_KEY`)
und legt sie auf dem **Branch `daten`** ab (nicht auf `main`). Lesen im Lauf:
`git fetch -q origin daten && git show FETCH_HEAD:kommentare.json` (ebenso `statistik.json`, `verlauf.csv`, `berichte/<Jahr>-KW<NN>.md`).
Fehlen die Dateien oder sind sie älter als 2 Tage, Luca kurz Bescheid geben und ohne Kommentarwünsche weitermachen.

## Ideen und Wünsche (Issues)
Luca kann Ideen als GitHub-Issue anlegen (Vorlagen „Idee“ und „Zuschauerwunsch“, Labels `idee` / `zuschauerwunsch`).
Im Lauf lesen: `gh api "repos/RevLucaa/Hirnalarm/issues?state=open&labels=idee" --jq '.[]|[.number,.title,.body]|@tsv'` (ebenso `zuschauerwunsch`).
Passendes in `naechste` einplanen; Issues nicht selbst schließen (Luca entscheidet).

## Renderer ändern
Jede Änderung an Aussehen oder Ton: `render.VERSION` erhöhen, Eintrag in `CHANGELOG.md`, `python3 tools/bildtest.py` ausführen.
Ist die Änderung gewollt, Referenzbilder mit `python3 tools/bildtest.py --neu` erneuern und mitcommitten. Vor dem Mergen nach `main`
einen Cloud-Test (`rendern.yml`, `test=true`, Pfad `tests/demo_stimmen`) machen und das Video ansehen.

## Grenzen
- ElevenLabs: **höchstens 2.000 Credits pro Video** (Wunsch von Luca; ≈ 1 Credit pro Zeichen, auch bei mehreren Stimmen – Summe aller Texte zählt, Neuversuche mitgerechnet).
- ElevenLabs: Creator-Plan (ca. 128.000 Credits/Monat, Stand 20.11.2026; auch für die Gruselgeschichten). Vor dem Erzeugen `account_get_usage` prüfen; wenn < 2.000 übrig, abbrechen und Luca Bescheid geben.
- Nie öffentlich posten, wenn das Rendern/Prüfen fehlschlägt – lieber Lauf abbrechen und melden.
