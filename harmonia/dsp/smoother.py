# harmonia/dsp/smoother.py
from collections import deque, Counter


class ChordSmoother:
    def __init__(self, k=7):
        self.buf = deque(maxlen=k)

    def update(self, chord):
        """chord: назва акорду або None (тиша). Повертає згладжений акорд."""
        self.buf.append(chord)
        winner, count = Counter(self.buf).most_common(1)[0]
        return winner