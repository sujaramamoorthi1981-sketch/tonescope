import os

os.environ["DATABASE_URL"] = "sqlite:///./tonescope_test.db"

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.session import Base, engine
from app.main import app
from tests.audio_utils import make_wav

SPEC = {"happy": (300, 0.02, 0.3), "sad": (110, 0.01, 0.0), "angry": (220, 0.15, 0.6),
        "fear": (380, 0.05, 0.5), "surprise": (450, 0.03, 0.2), "neutral": (160, 0.02, 0.0)}


@pytest.fixture(scope="session")
def tiny_model(tmp_path_factory):
    """Trains a throwaway model on synthetic tones so the API path can be exercised. Not a real emotion model."""
    from pathlib import Path

    from app.ml.train import fit_and_save

    d = tmp_path_factory.mktemp("clips")
    samples = []
    for label, (f, n, tr) in SPEC.items():
        for i in range(10):
            p = Path(d) / f"{label}_{i}.wav"
            p.write_bytes(make_wav(f * (1 + 0.03 * i), n, tremolo=tr, seed=i))
            samples.append((p, label, None))
    out = Path(d) / "model.joblib"
    fit_and_save(samples, out)
    return out


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def with_model(tiny_model):
    from app.ml.detector import emotion_model

    old = settings.model_path
    settings.model_path = str(tiny_model)
    emotion_model.reload()
    yield
    settings.model_path = old
    emotion_model.reload()


@pytest.fixture()
def auth_headers(client):
    r = client.post("/api/auth/register", json={"name": "Test", "email": "t@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['data']['token']}"}
