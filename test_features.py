import pytest

from app.ml.features import AudioError, extract
from tests.audio_utils import make_wav


def test_pitch_is_recovered():
    _, a = extract(make_wav(200))
    assert 180 < a["pitch_mean_hz"] < 220


def test_vector_is_fixed_length():
    v1, _ = extract(make_wav(150)); v2, _ = extract(make_wav(300, noise=0.1, seconds=2))
    assert v1.shape == v2.shape


def test_rejects_garbage_and_silence():
    with pytest.raises(AudioError):
        extract(b"not audio")
    with pytest.raises(AudioError):
        extract(make_wav(200, seconds=0.2))
