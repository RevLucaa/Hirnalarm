# Änderungsprotokoll

Versionen des Renderers (`render/__init__.py` → `VERSION`). Jede Folge nennt im Release die Version, mit der sie gerendert wurde.

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
