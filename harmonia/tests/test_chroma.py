# tests/test_chroma.py
import sys
from pathlib import Path

# Додаємо кореневу папку проекту в шлях пошуку модулів Python
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from harmonia.dsp.chroma import chroma_from_frame, NOTE_NAMES, FS, N


def synth_chord(freqs, n_harm=4):
    t = np.arange(N) / FS
    sig = np.zeros(N)
    for f in freqs:
        for h in range(1, n_harm + 1):          # імітація гармонік струни
            sig += (1.0 / h) * np.sin(2 * np.pi * f * h * t)
    return (sig / np.max(np.abs(sig))).astype(np.float32)

c_major = synth_chord([261.63, 329.63, 392.00])   # C4 E4 G4
chroma = chroma_from_frame(c_major)

top3 = np.argsort(chroma)[::-1][:3]
print({NOTE_NAMES[i]: round(float(chroma[i]), 3) for i in top3})
# Очікуємо: C, E, G на верху


from harmonia.dsp.chords import detect_chord

CASES = {
    "C":  [261.63, 329.63, 392.00],   # C4 E4 G4
    "Am": [220.00, 261.63, 329.63],   # A3 C4 E4
    "G":  [196.00, 246.94, 293.66],   # G3 B3 D4
    "F":  [174.61, 220.00, 261.63],   # F3 A3 C4
    "Dm": [146.83, 174.61, 220.00],   # D3 F3 A3
    "Em": [164.81, 196.00, 246.94],   # E3 G3 B3
}

failed = 0
for expected, freqs in CASES.items():
    name, score = detect_chord(chroma_from_frame(synth_chord(freqs)))
    ok = name == expected
    failed += not ok
    print(f"{'OK  ' if ok else 'FAIL'} expected={expected:3s} got={name} score={score:.3f}")

print(f"\n{len(CASES) - failed}/{len(CASES)} passed")