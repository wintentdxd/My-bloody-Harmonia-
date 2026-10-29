# dsp/chroma.py
import numpy as np

FS = 16000
N = 8192
FMIN, FMAX = 65.0, 2000.0
A4 = 440.0
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def build_bin_map(fs=FS, n=N, fmin=FMIN, fmax=FMAX):
    """LUT: які FFT-біни в який pitch class потрапляють (рахуємо 1 раз)."""
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    idx = np.where((freqs >= fmin) & (freqs <= fmax))[0]
    midi = 69.0 + 12.0 * np.log2(freqs[idx] / A4)
    pc = np.mod(np.round(midi).astype(int), 12)   # C=0 ... B=11
    return idx, pc


_IDX, _PC = build_bin_map()
_WINDOW = np.hanning(N).astype(np.float32)        # теж LUT


def chroma_from_frame(frame: np.ndarray) -> np.ndarray:
    """frame: N відліків float32 -> нормований chroma-вектор (12,)."""
    assert len(frame) == N
    spec = np.abs(np.fft.rfft(frame * _WINDOW))
    mag = spec[_IDX]
    chroma = np.bincount(_PC, weights=mag, minlength=12)
    norm = np.linalg.norm(chroma)
    return chroma / norm if norm > 1e-9 else chroma


def frame_rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame * frame)))