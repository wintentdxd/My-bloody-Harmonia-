# harmonia/io/wav_source.py
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from math import gcd

from harmonia.dsp.chroma import FS, N

HOP = 2048


def load_wav(path, target_fs=FS):
    """WAV -> моно float32 [-1, 1] на частоті target_fs."""
    fs, data = wavfile.read(path)
    data = data.astype(np.float32)
    if data.ndim == 2:                       # стерео -> моно
        data = data.mean(axis=1)
    peak = np.max(np.abs(data))
    if peak > 0:
        data /= peak                         # нормалізація гучності
    if fs != target_fs:
        g = gcd(fs, target_fs)
        data = resample_poly(data, target_fs // g, fs // g).astype(np.float32)
    return data


def frames(signal, n=N, hop=HOP):
    """Генератор кадрів довжини n зі зсувом hop."""
    for start in range(0, len(signal) - n + 1, hop):
        yield signal[start:start + n]