# Änderungsprotokoll

Versionen des Renderers (`render/__init__.py` → `VERSION`). Jede Folge nennt im Release die Version, mit der sie gerendert wurde.

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
