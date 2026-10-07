"""Audio feature extraction (numpy/scipy only). Input: 16-bit/float WAV bytes.

Produces a fixed-length vector of summary statistics (MFCC, delta-MFCC, spectral shape, energy,
zero-crossing rate, pitch) plus a human-readable acoustic summary. Bump FEATURE_VERSION if the
vector layout changes so stale models are rejected instead of silently misbehaving.
"""
import io
from math import gcd

import numpy as np
from scipy import signal
from scipy.fft import dct, irfft, rfft
from scipy.io import wavfile

SR = 16000
FRAME, HOP, NFFT = 400, 160, 512          # 25 ms window, 10 ms hop
N_MELS, N_MFCC = 40, 20
PITCH_FRAME, PITCH_HOP = 1024, 320
MIN_SECONDS, MAX_SECONDS = 0.5, 30.0
FEATURE_VERSION = 1


class AudioError(Exception):
    """User-facing problem with the submitted audio."""


def load_wav(data: bytes) -> np.ndarray:
    try:
        sr, x = wavfile.read(io.BytesIO(data))
    except Exception as exc:
        raise AudioError("Could not read the audio. Please send a valid WAV file.") from exc
    if x.dtype == np.uint8:
        x = (x.astype(np.float64) - 128) / 128
    elif np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float64) / (np.iinfo(x.dtype).max + 1)
    else:
        x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if not np.all(np.isfinite(x)):
        raise AudioError("The audio contains invalid samples.")
    if sr != SR:
        g = gcd(SR, int(sr))
        x = signal.resample_poly(x, SR // g, int(sr) // g)
    return x


def _frames(x: np.ndarray, size: int, hop: int) -> np.ndarray:
    if len(x) < size:
        x = np.pad(x, (0, size - len(x)))
    return np.lib.stride_tricks.sliding_window_view(x, size)[::hop]


def _trim_silence(x: np.ndarray) -> tuple[np.ndarray, float]:
    peak = float(np.max(np.abs(x)))
    if peak < 1e-4:
        raise AudioError("The recording is silent. Check your microphone and try again.")
    x = x / peak
    rms = np.sqrt(np.mean(_frames(x, FRAME, HOP) ** 2, axis=1))
    active = np.where(rms > 0.1 * rms.max())[0]
    start, end = active[0] * HOP, active[-1] * HOP + FRAME
    if (end - start) / SR < MIN_SECONDS * 0.6:
        raise AudioError("Not enough speech detected. Please speak for at least a second.")
    return x[start:end], float(len(active) / len(rms))


_MEL_FB: np.ndarray | None = None


def _mel_filterbank() -> np.ndarray:
    global _MEL_FB
    if _MEL_FB is None:
        hz2mel = lambda f: 2595 * np.log10(1 + f / 700)
        mel2hz = lambda m: 700 * (10 ** (m / 2595) - 1)
        hz = mel2hz(np.linspace(hz2mel(0), hz2mel(SR / 2), N_MELS + 2))
        bins = np.floor((NFFT + 1) * hz / SR).astype(int)
        fb = np.zeros((N_MELS, NFFT // 2 + 1))
        for i in range(1, N_MELS + 1):
            lo, mid, hi = bins[i - 1], bins[i], bins[i + 1]
            fb[i - 1, lo:mid] = (np.arange(lo, mid) - lo) / max(mid - lo, 1)
            fb[i - 1, mid:hi] = (hi - np.arange(mid, hi)) / max(hi - mid, 1)
        _MEL_FB = fb
    return _MEL_FB


def _pitch(x: np.ndarray) -> np.ndarray:
    """Per-frame f0 (Hz) via autocorrelation; unvoiced frames are dropped."""
    frames = _frames(x, PITCH_FRAME, PITCH_HOP)
    energy = np.sqrt(np.mean(frames ** 2, axis=1))
    win = frames * np.hanning(PITCH_FRAME)
    ac = irfft(np.abs(rfft(win, 2048)) ** 2)[:, :400]
    ac = ac / (ac[:, :1] + 1e-12)
    lo, hi = SR // 400, SR // 60                       # 60-400 Hz
    seg = ac[:, lo:hi]
    lag = seg.argmax(axis=1) + lo
    voiced = (seg.max(axis=1) > 0.35) & (energy > 0.05)
    return SR / lag[voiced]


def extract(data: bytes) -> tuple[np.ndarray, dict]:
    x = load_wav(data)
    duration = len(x) / SR
    if duration < MIN_SECONDS:
        raise AudioError("The recording is too short. Please record at least half a second.")
    if duration > MAX_SECONDS:
        raise AudioError(f"The recording is too long. The limit is {int(MAX_SECONDS)} seconds.")
    x, activity = _trim_silence(x)

    raw = _frames(x, FRAME, HOP)
    spec = np.abs(rfft(raw * np.hamming(FRAME), NFFT)) ** 2
    mel = np.log(spec @ _mel_filterbank().T + 1e-10)
    mfcc = dct(mel, type=2, axis=1, norm="ortho")[:, :N_MFCC]
    delta = np.gradient(mfcc, axis=0)

    freqs = np.linspace(0, SR / 2, spec.shape[1])
    mag = np.sqrt(spec)
    centroid = (mag * freqs).sum(1) / (mag.sum(1) + 1e-10)
    cum = np.cumsum(spec, axis=1)
    rolloff = freqs[(cum >= 0.85 * cum[:, -1:]).argmax(axis=1)]
    flatness = np.exp(np.mean(np.log(spec + 1e-10), axis=1)) / (np.mean(spec, axis=1) + 1e-10)
    zcr = np.mean(np.abs(np.diff(np.sign(raw), axis=1)) > 0, axis=1)
    rms = np.sqrt(np.mean(raw ** 2, axis=1))

    f0 = _pitch(x)
    n_pitch_frames = max(len(_frames(x, PITCH_FRAME, PITCH_HOP)), 1)
    voiced_ratio = len(f0) / n_pitch_frames
    if len(f0) >= 5:
        p_mean, p_std, p_range = float(f0.mean()), float(f0.std()), float(np.percentile(f0, 95) - np.percentile(f0, 5))
    else:
        p_mean = p_std = p_range = 0.0

    vector = np.concatenate([
        mfcc.mean(0), mfcc.std(0), delta.std(0),
        [centroid.mean(), centroid.std(), rolloff.mean(), flatness.mean(),
         zcr.mean(), zcr.std(), rms.mean(), rms.std(), rms.max(),
         p_mean, p_std, p_range, voiced_ratio],
    ])
    acoustics = {
        "duration_seconds": round(duration, 2),
        "speech_seconds": round(len(x) / SR, 2),
        "speech_activity": round(activity, 2),
        "pitch_mean_hz": round(p_mean, 1),
        "pitch_variation_hz": round(p_std, 1),
        "voiced_ratio": round(voiced_ratio, 2),
        "brightness_hz": round(float(centroid.mean()), 0),
    }
    return vector, acoustics
