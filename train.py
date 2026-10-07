"""Train the speech emotion classifier on a labelled WAV dataset.

    python -m app.ml.train --dataset ravdess --data /path/to/RAVDESS
    python -m app.ml.train --dataset cremad  --data /path/to/CREMA-D/AudioWAV
    python -m app.ml.train --dataset folders --data /path/to/dir   # dir/<emotion>/*.wav

Target classes: happy, sad, angry, fear, surprise, neutral. RAVDESS "calm" is merged into neutral and
"disgust" is skipped. CREMA-D has no surprise class, so a CREMA-D-only model cannot predict it.
Where speaker IDs are known the test split holds out whole speakers (speaker-independent evaluation).
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from app.core.config import settings
from app.ml.features import FEATURE_VERSION, AudioError, extract

EMOTIONS = ["happy", "sad", "angry", "fear", "surprise", "neutral"]
RAVDESS = {"01": "neutral", "02": "neutral", "03": "happy", "04": "sad", "05": "angry", "06": "fear", "08": "surprise"}
CREMAD = {"ANG": "angry", "FEA": "fear", "HAP": "happy", "NEU": "neutral", "SAD": "sad"}

Sample = tuple[Path, str, str | None]  # path, label, speaker/group


def collect(dataset: str, root: Path) -> list[Sample]:
    out: list[Sample] = []
    if dataset == "folders":
        for d in sorted(p for p in root.iterdir() if p.is_dir() and p.name.lower() in EMOTIONS):
            out += [(f, d.name.lower(), None) for f in d.rglob("*.wav")]
    else:
        for f in root.rglob("*.wav"):
            parts = f.stem.split("-") if dataset == "ravdess" else f.stem.split("_")
            try:
                if dataset == "ravdess":
                    label, group = RAVDESS.get(parts[2]), parts[6]
                else:
                    label, group = CREMAD.get(parts[2]), parts[0]
            except IndexError:
                continue
            if label:
                out.append((f, label, group))
    return out


def fit_and_save(samples: list[Sample], out_path: Path, test_size: float = 0.2) -> dict:
    X, y, groups = [], [], []
    for path, label, group in samples:
        try:
            vec, _ = extract(path.read_bytes())
        except AudioError:
            continue
        X.append(vec); y.append(label); groups.append(group)
    if len(set(y)) < 2:
        raise SystemExit("Need at least two emotion classes with readable audio.")
    X, y = np.array(X), np.array(y)

    speaker_independent = all(g is not None for g in groups) and len(set(groups)) >= 4
    if speaker_independent:
        tr, te = next(GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42).split(X, y, groups))
    else:
        tr, te = train_test_split(np.arange(len(y)), test_size=test_size, stratify=y, random_state=42)

    pipe = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=10, gamma="scale", probability=True, class_weight="balanced", random_state=42))
    pipe.fit(X[tr], y[tr])
    pred = pipe.predict(X[te])
    labels = [str(c) for c in pipe.classes_]
    metrics = {
        "dataset_size": int(len(y)), "train_size": int(len(tr)), "test_size": int(len(te)),
        "classes": labels, "speaker_independent_split": bool(speaker_independent),
        "accuracy": round(float(accuracy_score(y[te], pred)), 4),
        "macro_f1": round(float(f1_score(y[te], pred, average="macro")), 4),
        "per_class": classification_report(y[te], pred, labels=labels, output_dict=True, zero_division=0),
        "confusion_matrix": {"labels": labels, "matrix": confusion_matrix(y[te], pred, labels=labels).tolist()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "feature_version": FEATURE_VERSION}, out_path)
    out_path.with_suffix(".metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["ravdess", "cremad", "folders"], required=True)
    ap.add_argument("--data", required=True, help="Dataset root directory")
    args = ap.parse_args()
    samples = collect(args.dataset, Path(args.data))
    print(f"Found {len(samples)} labelled clips; extracting features (this can take a few minutes)…")
    metrics = fit_and_save(samples, Path(settings.model_path))
    print(json.dumps({k: v for k, v in metrics.items() if k != "per_class"}, indent=2))
    print(f"Saved model to {settings.model_path}. Restart the API to load it.")


if __name__ == "__main__":
    main()
