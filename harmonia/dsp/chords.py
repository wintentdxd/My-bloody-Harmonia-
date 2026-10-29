# harmonia/dsp/chords.py
import numpy as np

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

MAJOR = [0, 4, 7]   # корінь, велика терція, квінта
MINOR = [0, 3, 7]   # корінь, мала терція, квінта


def build_templates():
    """24 шаблони (12 мажорних + 12 мінорних), L2-нормовані. Рахуємо 1 раз."""
    names, mats = [], []
    for root in range(12):
        for suffix, intervals in (("", MAJOR), ("m", MINOR)):
            t = np.zeros(12, dtype=np.float32)
            for iv in intervals:
                t[(root + iv) % 12] = 1.0
            t /= np.linalg.norm(t)
            names.append(NOTE_NAMES[root] + suffix)
            mats.append(t)
    return names, np.stack(mats)          # (24,), (24, 12)


CHORD_NAMES, TEMPLATES = build_templates()


def detect_chord(chroma: np.ndarray, silence_thresh=0.5):
    """Повертає (назва, впевненість). None, якщо схоже на тишу / не акорд."""
    if np.linalg.norm(chroma) < 1e-9:
        return None, 0.0
    scores = TEMPLATES @ chroma           # chroma вже L2-нормований
    best = int(np.argmax(scores))
    if scores[best] < silence_thresh:
        return None, float(scores[best])
    return CHORD_NAMES[best], float(scores[best])