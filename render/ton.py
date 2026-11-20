"""Soundeffekte, Publikum und Beat der Hirnalarm-Engine (alles synthetisch, ohne fremde Dateien oder Lizenzen)."""
import wave

import numpy as np

SR = 44100


def _farbrauschen(n, lo, hi, rng):
    """Bandbegrenztes Rauschen (FFT-Filter) – Grundlage für Publikum, Wischer, Schläge."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    maske = ((f >= lo) & (f <= hi)).astype(np.float32)
    maske /= np.sqrt(np.maximum(f, 20) / 200)  # leicht rosa: weniger zischelig
    x = np.fft.irfft(spec * maske, n)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def _klaenge(rng):
    S = {}
    # Schlag: tiefer Körper + kurzer Knack + etwas Raum
    t = np.arange(int(0.7 * SR)) / SR
    koerper = np.sin(2 * np.pi * (110 * np.exp(-t * 9) + 45) * t) * np.exp(-t * 7)
    knack = _farbrauschen(len(t), 1500, 7000, rng) * np.exp(-t * 60)
    S["boom"] = (0.85 * koerper + 0.35 * knack) * 0.8
    S["boom_s"] = S["boom"] * 0.55
    S["thud"] = S["boom"][: int(0.3 * SR)] * 0.5
    # Wischer: Rauschen mit Filter-Sweep
    tw = np.arange(int(0.45 * SR)) / SR
    w = _farbrauschen(len(tw), 400, 5000, rng)
    S["whoosh"] = w * np.sin(np.pi * tw / tw[-1]) ** 2 * 0.28
    # Ringglocke: Inharmonische Teiltöne wie eine echte Boxglocke
    tb = np.arange(int(1.6 * SR)) / SR
    S["bell"] = sum(a * np.sin(2 * np.pi * f * tb) * np.exp(-tb * d) for f, a, d in
                    [(1180, 1.0, 3.0), (2760, 0.5, 4.5), (4310, 0.25, 6), (590, 0.3, 2.5)]) * 0.16
    # Pop (Punkt)
    tp = np.arange(int(0.25 * SR)) / SR
    S["pop"] = np.sin(2 * np.pi * (500 + 1500 * tp) * tp) * np.exp(-tp * 18) * 0.35
    to = np.arange(int(0.5 * SR)) / SR
    S["boing"] = np.sin(2 * np.pi * (180 + 120 * np.sin(2 * np.pi * 9 * to)) * to) * np.exp(-to * 5) * 0.4
    # Publikum jubelt: viele Stimmen = moduliertes Bandrauschen + kurze "Hey"-Spitzen
    tc = np.arange(int(2.8 * SR)) / SR
    jubel = _farbrauschen(len(tc), 300, 3500, rng)
    jubel *= 1 + 0.35 * np.sin(2 * np.pi * 5.5 * tc + rng.uniform(0, 6))
    huelle = np.minimum(1, tc / 0.25) * np.exp(-np.maximum(0, tc - 0.9) * 1.6)
    S["cheer"] = jubel * huelle * 0.32
    S["cheer_s"] = S["cheer"][: int(1.4 * SR)] * 0.6
    # Raunen "Ohhh" (bei Schock/Fehlschlag)
    S["ooh"] = _farbrauschen(len(tc[: int(1.5 * SR)]), 200, 1200, rng) * np.sin(np.pi * tc[: int(1.5 * SR)] / 1.5) * 0.22
    # Pfiff (Schiri / Fußball)
    tf = np.arange(int(0.6 * SR)) / SR
    S["whistle"] = np.sin(2 * np.pi * (2900 + 120 * np.sin(2 * np.pi * 32 * tf)) * tf) * np.minimum(1, tf / 0.02) * np.exp(-np.maximum(0, tf - 0.45) * 30) * 0.18
    return {k: v.astype(np.float32) for k, v in S.items()}


def sfx_track(path, TOTAL, SEG, SFX):
    n = int(TOTAL * SR) + SR
    tr = np.zeros(n, dtype=np.float32)

    def add(sig, t0):
        i = int(t0 * SR); j = min(n, i + len(sig))
        if 0 <= i < n:
            tr[i:j] += sig[: j - i]

    rng = np.random.default_rng(1)
    S_ = _klaenge(rng)

    # Hallen-Atmosphäre: leises Publikumsgemurmel über die ganze Folge
    bett = _farbrauschen(n, 250, 2500, rng) * (1 + 0.25 * np.sin(2 * np.pi * 0.13 * np.arange(n) / SR))
    tr += bett * 0.035

    for s, a, b in SEG:
        sc = s["scene"]
        if sc == "banner": add(S_["bell"], a)
        if sc == "point": add(S_["pop"], a + 0.15 * (b - a)); add(S_["cheer_s"], a + 0.1 * (b - a))
        if sc == "intro": add(S_["whoosh"], a + 0.05); add(S_["cheer_s"], a + 0.3)
        if sc == "win": add(S_["bell"], a); add(S_["pop"], a + 0.1); add(S_["cheer"], a + 0.05)
    for t0, kind in SFX:
        add(S_[kind], t0)
        if kind == "boom": add(S_["ooh"], t0 + 0.15)

    # Beat: Kick, Clap auf 2 und 4, Hi-Hat – leise unter der Stimme
    beat = 60 / 128
    tk = np.arange(int(0.18 * SR)) / SR
    kick = np.sin(2 * np.pi * (120 - 80 * tk / tk[-1]) * tk) * np.exp(-tk * 20) * 0.22
    hat = _farbrauschen(int(0.04 * SR), 6000, 16000, rng) * np.exp(-np.arange(int(0.04 * SR)) / SR * 90) * 0.05
    clap = _farbrauschen(int(0.12 * SR), 900, 5000, rng) * np.exp(-np.arange(int(0.12 * SR)) / SR * 35) * 0.07
    x, k = 0.0, 0
    while x < TOTAL:
        add(kick, x); add(hat, x + beat / 2)
        if k % 2 == 1: add(clap, x)
        x += beat; k += 1
    tr = np.tanh(tr * 1.1) / np.tanh(1.1)  # weich begrenzen statt hart abschneiden
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((tr * 32767).astype(np.int16).tobytes())
