#!/usr/bin/env python3
"""Phrasengrenzen ('bounds') für episode.json aus den Einzel-Teilen berechnen.

Die Sprecherwechsel sind durch teile/NN.mp3 exakt bekannt; innerhalb eines Blocks werden die
Grenzen auf Pausen gelegt (Silbenschätzung als Rückfall). Gleiche Kette wie stimme_bauen.py
(Ränder weg, 0,35 s Pause, Tempo aus stimme.mp3).
    python3 tools/grenzen.py episodes/F12_xyz          -> zeigt Grenzen
    python3 tools/grenzen.py episodes/F12_xyz --setzen -> schreibt 'bounds' in episode.json
"""
import glob, json, os, re, subprocess, sys, tempfile

def syl(t):
    t = t.lower(); return max(1, len(re.findall(r"[aeiouäöüy]+", t)))

def dauer(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)

def main():
    ordner = sys.argv[1].rstrip("/"); ep_p = os.path.join(ordner, "episode.json")
    ep = json.load(open(ep_p, encoding="utf-8"))
    phr = []
    for s in ep["segments"]:
        for p in [p.strip() for p in re.split(r"(?<=[.!?:])\s+", s["text"]) if p.strip()]:
            phr.append((s.get("speaker") or "Erzähler", p))
    bl = []
    for sp, p in phr:
        if bl and bl[-1][0] == sp: bl[-1][1].append(p)
        else: bl.append((sp, [p]))
    teile = sorted(glob.glob(os.path.join(ordner, "teile", "[0-9]*.mp3")))
    assert len(teile) == len(bl), f"{len(bl)} Sprecherblöcke im JSON, {len(teile)} Teile"
    roh, info = 0.0, []
    for p in teile:
        tmp = tempfile.mktemp(suffix=".wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", p, "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "44100", "-ac", "1", tmp], check=True)
        d = dauer(tmp)
        r = subprocess.run(["ffmpeg", "-i", tmp, "-af", "silencedetect=noise=-40dB:d=0.06", "-f", "null", "-"], capture_output=True, text=True).stderr
        st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
        info.append((roh, d, [((a + b) / 2, b - a) for a, b in zip(st, en) if 0.15 < a and b < d - 0.15]))
        os.remove(tmp); roh += d + 0.35
    roh -= 0.35
    tempo = roh / dauer(os.path.join(ordner, "stimme.mp3"))
    bounds = []
    for bi, ((sp, ps), (t0, d, sil)) in enumerate(zip(bl, info)):
        S = [syl(p) + (4 if "[laugh]" in p else 0) for p in ps]
        n = len(ps)
        if n > 1:
            rate = d / sum(S)
            cands = sil + [(rate * sum(S[:k]), -0.25) for k in range(1, n)]  # Rückfall: Silbenschätzung
            cands.sort()
            INF = 1e18; M = len(cands)
            cost = lambda dd, s, g: ((dd - rate * s) / (rate * s)) ** 2 - 3.0 * g
            dp = [[INF] * M for _ in range(n - 1)]; bk = [[-1] * M for _ in range(n - 1)]
            for j in range(M): dp[0][j] = cost(cands[j][0], S[0], cands[j][1])
            for i in range(1, n - 1):
                for j in range(M):
                    for k in range(j):
                        if dp[i - 1][k] < INF and cands[j][0] - cands[k][0] > 0.2:
                            v = dp[i - 1][k] + cost(cands[j][0] - cands[k][0], S[i], cands[j][1])
                            if v < dp[i][j]: dp[i][j], bk[i][j] = v, k
            best, bj = INF, -1
            for j in range(M):
                if dp[n - 2][j] < INF:
                    v = dp[n - 2][j] + cost(d - cands[j][0], S[n - 1], 0)
                    if v < best: best, bj = v, j
            inn = [0.0] * (n - 1); j = bj
            for i in range(n - 2, -1, -1): inn[i] = cands[j][0]; j = bk[i][j]
            bounds += [round((t0 + x) / tempo, 2) for x in inn]
        if bi < len(bl) - 1:
            bounds.append(round((t0 + d + 0.175) / tempo, 2))
    allp = [p for _, ps in bl for p in ps]; prev = 0
    for p, b in zip(allp, bounds + [round(roh / tempo, 2)]):
        print(f"{prev:6.2f}-{b:6.2f} {p}"); prev = b
    if "--setzen" in sys.argv:
        ep["bounds"] = bounds; json.dump(ep, open(ep_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("bounds gesetzt", file=sys.stderr)

if __name__ == "__main__":
    main()
