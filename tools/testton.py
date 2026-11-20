#!/usr/bin/env python3
"""Erzeugt eine künstliche 56-s-„Stimme“ (Töne mit Pausen) für Tests ohne ElevenLabs.
Aufruf: python3 tools/testton.py ziel.mp3
"""
import subprocess
import sys
import wave

import numpy as np

sr = 44100
rng = np.random.default_rng(0)
teile = []
for _ in range(60):
    n = int(sr * rng.uniform(0.6, 1.4))
    teile.append(0.3 * np.sin(2 * np.pi * 220 * np.arange(n) / sr))
    teile.append(np.zeros(int(sr * rng.uniform(0.15, 0.35))))
ton = np.concatenate(teile)[: sr * 56]
ziel = sys.argv[1]
with wave.open(ziel + ".wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((ton * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", ziel + ".wav", ziel], check=True)
