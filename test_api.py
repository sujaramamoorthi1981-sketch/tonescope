from tests.audio_utils import make_wav


def _upload(client, headers, wav, name="a.wav"):
    return client.post("/api/analyze", files={"file": (name, wav, "audio/wav")}, headers=headers)


def test_auth_required(client):
    assert client.post("/api/analyze", files={"file": ("a.wav", make_wav(200), "audio/wav")}).status_code == 401


def test_without_model_returns_acoustics_only(client, auth_headers):
    d = _upload(client, auth_headers, make_wav(200)).json()["data"]
    assert d["model_available"] is False and d["emotion"] is None and d["acoustics"]["pitch_mean_hz"] > 0
    assert client.get("/api/history", headers=auth_headers).json()["data"] == []


def test_analyze_history_stats(client, auth_headers, with_model):
    r = _upload(client, auth_headers, make_wav(110))
    d = r.json()["data"]
    assert r.status_code == 200 and d["emotion"] in d["probabilities"] and abs(sum(d["probabilities"].values()) - 1) < 0.01
    hist = client.get("/api/history", headers=auth_headers).json()["data"]
    assert len(hist) == 1
    assert client.get("/api/stats", headers=auth_headers).json()["data"]["total"] == 1
    assert client.delete(f"/api/history/{hist[0]['id']}", headers=auth_headers).status_code == 200


def test_bad_uploads(client, auth_headers):
    assert _upload(client, auth_headers, b"hello").status_code == 415
    assert _upload(client, auth_headers, make_wav(200, seconds=0.2)).status_code == 422
