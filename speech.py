import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.config import settings
from app.core.errors import AppError
from app.database.session import get_db
from app.ml.detector import emotion_model
from app.ml.features import AudioError, extract
from app.models import Analysis, User, utcnow
from app.schemas import ok

router = APIRouter(prefix="/api", tags=["speech"])
log = logging.getLogger("tonescope.speech")


def _row(a: Analysis) -> dict:
    return {
        "id": a.id, "filename": a.filename, "duration_seconds": a.duration_seconds, "emotion": a.emotion,
        "confidence": a.confidence, "probabilities": a.probabilities, "acoustics": a.acoustics,
        "created_at": a.created_at.isoformat(),
    }


@router.post("/analyze")
def analyze(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = file.file.read(settings.max_audio_bytes + 1)
    if len(data) > settings.max_audio_bytes:
        raise AppError("FILE_TOO_LARGE", "That audio file is too large.", 413)
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise AppError("INVALID_AUDIO", "Please send a WAV file.", 415)
    try:
        vector, acoustics = extract(data)
    except AudioError as exc:
        raise AppError("INVALID_AUDIO", str(exc), 422)
    except Exception:
        log.exception("Feature extraction failed")
        raise AppError("INVALID_AUDIO", "We couldn't process that audio. Try recording again.", 422)

    if not emotion_model.available:
        return ok(
            {"model_available": False, "id": None, "emotion": None, "confidence": None, "probabilities": {}, "acoustics": acoustics,
             "note": emotion_model.info["note"]},
            "Acoustic analysis only: no emotion model is loaded",
        )
    pred = emotion_model.predict(vector)
    name = os.path.basename(file.filename or "recording.wav")[:120]
    row = Analysis(user_id=user.id, filename=name, duration_seconds=acoustics["duration_seconds"], acoustics=acoustics, **pred)
    db.add(row)
    db.commit()
    return ok({**_row(row), "model_available": True, "note": None}, "Recording analyzed")


@router.get("/history")
def history(
    emotion: str | None = Query(default=None, pattern="^(happy|sad|angry|fear|surprise|neutral)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = select(Analysis).where(Analysis.user_id == user.id)
    if emotion:
        q = q.where(Analysis.emotion == emotion)
    return ok([_row(a) for a in db.scalars(q.order_by(Analysis.id.desc()).limit(limit).offset(offset)).all()])


@router.delete("/history/{analysis_id}")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = db.get(Analysis, analysis_id)
    if not a or a.user_id != user.id:
        raise AppError("NOT_FOUND", "Result not found.", 404)
    db.delete(a)
    db.commit()
    return ok(None, "Deleted")


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    mine = Analysis.user_id == user.id
    total = db.scalar(select(func.count()).select_from(Analysis).where(mine)) or 0
    avg_conf = db.scalar(select(func.avg(Analysis.confidence)).where(mine))
    by_emotion = {e: n for e, n in db.execute(select(Analysis.emotion, func.count()).where(mine).group_by(Analysis.emotion)).all()}
    since = utcnow() - timedelta(days=13)
    per_day = db.execute(
        select(func.date(Analysis.created_at), func.count()).where(mine, Analysis.created_at >= since).group_by(func.date(Analysis.created_at))
    ).all()
    return ok({
        "total": total, "average_confidence": round(float(avg_conf), 3) if avg_conf else 0.0, "by_emotion": by_emotion,
        "per_day": [{"date": str(d), "count": n} for d, n in sorted(per_day)],
    })


@router.get("/model")
def model_info(_: User = Depends(current_user)):
    return ok(emotion_model.info)
