# harmonia/engine.py
"""Конвеєр: кадр -> chroma -> акорд -> debounce -> тональність -> поради."""
from collections import deque
import numpy as np

from harmonia.dsp.chroma import analyze_frame, HOP, FS
from harmonia.dsp.chords import detect_chord, explain
from harmonia.dsp.smoother import ChordSmoother
from harmonia.theory.circle import estimate_key
from harmonia.theory.instruments import advise


class RealtimeEngine:
    def __init__(self, gate=None, calib_frames=16, gate_mult=3.0, min_gate=0.004,
                 history=12, avoid_fret=None, on_event=None, detect_kwargs=None):
        self.gate = gate                    # None -> автокалібрування по шуму кімнати
        self.calib_frames, self.gate_mult, self.min_gate = calib_frames, gate_mult, min_gate
        self._calib = []
        self.gate_open = False
        self.smoother = ChordSmoother()
        self.history = deque(maxlen=history)
        self.avoid_fret = avoid_fret
        self.on_event = on_event
        self.detect_kwargs = detect_kwargs or {}
        self._prev_rms = 0.0
        self._skips = 0
        self._last = None

    def process_frame(self, frame):
        chroma, rms = analyze_frame(frame)
        ev = {"t_ms": round(1000 * HOP / FS), "rms": rms, "gate": self.gate,
              "raw": None, "score": 0.0, "stable": self._last, "changed": False,
              "calibrating": False, "advice": None, "debug": None}

        if self.gate is None:               # перші ~1 с: мовчи, міряємо шум
            self._calib.append(rms)
            if len(self._calib) >= self.calib_frames:
                self.gate = max(self.min_gate, self.gate_mult * float(np.median(self._calib)))
            ev["calibrating"] = True
            return self._emit(ev)

        thr = self.gate * (0.7 if self.gate_open else 1.0)       # гістерезис
        self.gate_open = rms >= thr

        transient = self.gate_open and self._prev_rms > 0 and rms > 2.5 * self._prev_rms and self._skips < 3
        self._prev_rms = rms
        if transient:                       # різкий стрибок енергії = атака; не голосуємо
            self._skips += 1
            return self._emit(ev)
        self._skips = 0

        if self.gate_open:
            raw, score = detect_chord(chroma, **self.detect_kwargs)
            ev["debug"] = explain(chroma, **self.detect_kwargs)
        else:
            raw, score = None, 0.0
        ev["raw"], ev["score"] = raw, score
        stable = self.smoother.update(raw)
        ev["stable"] = stable

        if stable != self._last:
            ev["changed"] = True
            self._last = stable
            if stable:
                if not self.history or self.history[-1] != stable:
                    self.history.append(stable)
                key = estimate_key(list(self.history))
                ev["advice"] = advise(stable, key, self.avoid_fret)
        return self._emit(ev)

    def _emit(self, ev):
        if self.on_event:
            self.on_event(ev)
        return ev

    def run(self, frame_iter):
        for fr in frame_iter:
            self.process_frame(fr)
