import io

import numpy as np
from scipy.io import wavfile

SR = 16000


def make_wav(freq: float, noise: float = 0.0, seconds: float = 1.2, tremolo: float = 0.0, seed: int = 0) -> bytes:
    """Synthetic voiced-like clip for tests only (harmonic tone + noise)."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * seconds)) / SR
    x = sum(np.sin(2 * np.pi * freq * k * t) / k for k in (1, 2, 3))
    x *= 1 + tremolo * np.sin(2 * np.pi * 5 * t)
    x = x / np.max(np.abs(x)) * 0.6 + noise * rng.standard_normal(len(t))
    buf = io.BytesIO()
    wavfile.write(buf, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    return buf.getvalue()
