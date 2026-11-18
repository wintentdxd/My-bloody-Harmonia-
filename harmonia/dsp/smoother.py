# harmonia/dsp/smoother.py
from collections import deque, Counter

from harmonia.dsp.chords import related


class ChordSmoother:
    """Debounce: акорд змінюється, коли новий кандидат домінує в історії кадрів.

    confirm         — голосів із k для зміни на ІНШИЙ акорд;
    related_confirm — для СПОРІДНЕНОГО (C <-> Cmaj7 <-> Em, C <-> Am7): більше, щоб
                      наявність/відсутність 7-ї ноти не змушувала акорд «стрибати»;
    release         — голосів «тиші» для скидання (акорд затухає повільно).
    """

    def __init__(self, k=6, confirm=4, release=5, related_confirm=5):
        self.buf = deque(maxlen=k)
        self.confirm, self.release, self.related_confirm = confirm, release, related_confirm
        self.current = None

    def update(self, chord):
        self.buf.append(chord)
        for cand, cnt in Counter(self.buf).most_common():
            if cand == self.current:
                continue
            if cand is None:
                need = self.release
            elif self.current and related(cand, self.current):
                need = self.related_confirm
            else:
                need = self.confirm
            if cnt >= need:
                self.current = cand
                break
        return self.current
