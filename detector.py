"""Loads the trained emotion model if present. No model means no emotion output: this app never guesses."""
import json
import logging
from pathlib import Path
from threading import Lock

import numpy as np

from app.core.config import settings
from app.ml.features import FEATURE_VERSION

log = logging.getLogger("tonescope.detector")


class EmotionModel:
    def __init__(self) -> None:
        self._pipeline = None
        self._metrics: dict | None = None
        self._lock = Lock()
        self.reload()

    def reload(self) -> None:
        path = Path(settings.model_path)
        with self._lock:
            self._pipeline, self._metrics = None, None
            if not path.exists():
                log.warning("No trained model at %s. Run `python -m app.ml.train`.", path)
                return
            try:
                import joblib

                bundle = joblib.load(path)
                if bundle.get("feature_version") != FEATURE_VERSION:
                    log.error("Model feature version mismatch; retrain the model.")
                    return
                self._pipeline = bundle["pipeline"]
                m = path.with_suffix(".metrics.json")
                self._metrics = json.loads(m.read_text()) if m.exists() else None
                log.info("Loaded emotion model from %s", path)
            except Exception:
                log.exception("Could not load emotion model")
                self._pipeline = None

    @property
    def available(self) -> bool:
        return self._pipeline is not None

    @property
    def info(self) -> dict:
        return {
            "available": self.available,
            "metrics": self._metrics,
            "note": None if self.available else "No trained model found. Train one with `python -m app.ml.train` (see README).",
        }

    def predict(self, vector: np.ndarray) -> dict:
        with self._lock:
            proba = self._pipeline.predict_proba([vector])[0]
            classes = [str(c) for c in self._pipeline.classes_]
        probs = {c: round(float(p), 4) for c, p in zip(classes, proba)}
        top = max(probs, key=probs.get)
        return {"emotion": top, "confidence": probs[top], "probabilities": probs}


emotion_model = EmotionModel()
