# Änderungsprotokoll

Versionen des Renderers (`render/__init__.py` → `VERSION`). Jede Folge nennt im Release die Version, mit der sie gerendert wurde.

## 1.9.0 – 25.11.2026
- Neue Renn-Aktion `rutsch` (A = Gewinner): V wirft vor Schreck eine Sahnedose weg, sie landet vor den eigenen Füßen, V rutscht aus und dreht sich, A läuft als Erster ins Ziel (`wurf`, `hit`, `pfuetze_x`, `ziel_x`, `ziel_u`, `word`, `word2`)
- Neue Ring-Aktion `kitzeln` (A = Punktgewinner): A kitzelt V mit einem Haar am Bauch, V lacht, wackelt und kippt um (`hit`, `word`, `word2`); neues Extra `haar`
- `ueberholen`: Gesichtsausdruck der stehenden Figur einstellbar (`v_expr`, Standard `grin` wie bisher)
- `race`: Start verzögerbar (`los`), davor optional ein Zuruf als Sprechblase (`ruf`); Position der PLUMPS-Blase einstellbar (`plumps_x`)
- Bahn: die Figur auf der vorderen Bahn wird jetzt immer vor der hinteren gezeichnet (vorher lag der Schatten der hinteren Figur manchmal über dem Gesicht der vorderen; ändert das Aussehen von Renn-Aktionen in F12/F16 minimal)
- Sahne-Pfütze (`puddle`) kann auf beliebiger Höhe liegen (Bahn)
- Bestehende Aktionen und Folgen unverändert

## 1.8.0 – 24.11.2026
- Neue Fußball-Aktion `elfer2` (A = Schütze und Punktgewinner) mit `art`: `eiern` (Ball eiert im Zickzack, Torwart springt ins Leere), `leer` (Torwart kullert vor Aufregung aus dem Tor, Ball rollt ins leere Tor; `weg`), `sahne` (Sahne-Ball platzt im Gesicht des Torwarts, Klecks bleibt, Ball kullert ins Netz; `platsch`)
- Neue Ring-Aktion `schwindel` (A eiert immer schneller im Kreis um V, V wird schwindelig und kippt um; `los`, `hit`, `radius`, `mitte_x`)
- `clash`: Zeitpunkt des Aufpralls einstellbar (`hit`, Standard 0.36 wie bisher), Spritzer-Farbe `splash_farbe`
- Neues Extra `klecks` (Sahne im Gesicht)
- Bestehende Aktionen und Folgen unverändert (Bild-Test bitgenau gleich)

## 1.7.0 – 23.11.2026
- Neue Renn-Aktionen: `ueberholen` (Figur bleibt stehen und winkt in die Tribüne, die andere zieht vorbei; `word`, `word2`, `stopp`), `huepf` (Riesensprünge auf der Zielgeraden, Zielfoto „um ein Haar“; `foto`, `spruenge`, `haar_u`)
- Neue Ring-Aktion `handtuch` (Gast/Sekundant wirft ein Handtuch ins Gesicht, Figur tappt blind, wird aus dem Ring gerammt; `von_x`, `kleb`, `hit`, `tuch_y`)
- Bestehende Aktionen und Folgen unverändert

## 1.6.0 – 22.11.2026
- Neue Arena `"arena": "fussball"` (Stadion mit Fans in Vereinsfarben, Werbebande, Rasen mit Mähstreifen, Strafraum, Tor mit Netz)
- Neue Aktion `elfer` mit `art`: `kopf` (Torwart köpft den Ball zurück ins Gesicht des Schützen), `platzt` (Ball bleibt in den Stacheln stecken und platzt), `selbst` (Figur schießt sich selbst ins Tor und hängt im Netz)
- Namensschild auch für Nebenrollen, die nur im Teaser sprechen (`"nebenrollen": [{"short", "color"}]`)
- Figuren können mit `z` vor andere gezeichnet werden (Schütze vorn)
- Ring- und Bahn-Folgen unverändert

## 1.5.0 – 21.11.2026
- Neue Arena `"arena": "bahn"` (Laufbahn mit Tribüne, Werbebande, zwei Bahnen, bewegte Markierungen beim Laufen, Ziellinie)
- Neue Renn-Aktionen: `dash` (Start, optional `fehlstart`/`hatschi`), `propeller` (Figur hebt ab und landet in den Zuschauern), `surf` (Bananenschalen-Surfen ins Ziel mit Zielfoto)
- `post` kann eine Sahne-Pfütze zeigen (`cream: true`), `throw` kann Kerne kleben lassen (`kleben: true`)
- Gast-Figur mit eigener x-Position (`guest.x`); Schatten folgen der Bahn der Figur
- Ring-Folgen unverändert (Bild-Test bitgenau gleich)

## 1.4.0 – 20.11.2026
- Kamera: Zoom auf die sprechende Figur und den Sieger, Ruck und Wackeln bei Treffern (stärker im Finale)
- Figuren blinzeln und wippen beim Sprechen mit
- Kurzer Blitz als Übergang bei Rundenbanner und Sieg
- Renderer aufgeteilt: `render/aktionen.py`, `render/kulissen.py` (Ausgabe dabei bitgenau unverändert geprüft)
- Bild-Test gegen Referenzbilder in der Prüfung, feste Paketversionen, Python 3.13 in allen Actions
- YouTube-Daten und Wochenberichte auf eigenem Branch `daten`

## 1.3.0 – 20.11.2026
- Mundbewegung in drei Stufen (zu / halb / offen) nach Silben
- Neue Soundeffekte: Hallenpublikum, Jubel, „Ohhh“, Ringglocke, Schläge, Pfiff
- Loop-Ende und „erstes Bild = Action“ als Regel; Wochenbericht als Issue

## 1.2.0 – 20.11.2026
- Figurenstimmen (`stimmen.json`, `tools/stimme_bauen.py`), Namensschild über dem Untertitel

## 1.1.0 – 20.11.2026
- Rendern in GitHub Actions mit Release pro Folge, Prüfskript, Episoden-Ordner, README

## 1.0.0 – 16.11.2026
- Erste Folgen (F01–F09) mit `engine.py`
