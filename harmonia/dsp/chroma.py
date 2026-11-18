# harmonia/dsp/chroma.py
import numpy as np

FS = 16000
N = 8192            # довжина вікна (0.51 с) -> роздільність 1.95 Гц/бін
HOP = 1024          # крок (64 мс) -> 87.5% перекриття вікон
FMIN, FMAX = 60.0, 4000.0   # робоча смуга: усе поза нею відкидається
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
_WINDOW = np.hanning(N).astype(np.float32)
_WIN_ENERGY = float(np.sum(_WINDOW ** 2))


def analyze_frame(frame: np.ndarray, compress: float = 0.5, rel_floor: float = 0.1):
    """frame (N,) float32 -> (chroma (12,) L2-нормований, band_rms).

    band_rms — RMS лише в смузі 60..4000 Гц (через Парсеваля зі спектра),
    тож гул/шум поза смугою не відкриває noise gate.
    compress < 1 — степеневе стиснення амплітуд: гучні гармоніки/бас
    не «глушать» решту нот акорду.
    rel_floor — біни слабші за rel_floor*пік (−20 дБ) обнуляються ДО стиснення:
    інакше тисячі шумових бінів після sqrt «розмазують» chroma.
    """
    assert len(frame) == N
    x = (frame - frame.mean()) * _WINDOW            # прибрати DC + вікно Ханна
    mag = np.abs(np.fft.rfft(x))[_IDX]
    band_rms = float(np.sqrt(2.0 * np.sum(mag ** 2) / (N * _WIN_ENERGY)))
    peak = mag.max()
    mag = np.where(mag >= rel_floor * peak, mag, 0.0)
    chroma = np.bincount(_PC, weights=mag ** compress, minlength=12).astype(np.float32)
    norm = np.linalg.norm(chroma)
    return (chroma / norm if norm > 1e-9 else chroma), band_rms


def chroma_from_frame(frame: np.ndarray) -> np.ndarray:
    """Сумісність зі старим API."""
    return analyze_frame(frame)[0]


def frame_rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame * frame)))
