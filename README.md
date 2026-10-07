# ToneScope – Speech Emotion Recognition System

Record or upload speech and get the likely emotion (happy, sad, angry, fear, surprise, neutral), per-emotion
probabilities, and acoustic measurements (pitch, speech length). Accounts (bcrypt + JWT), history with filters,
and a dashboard. Audio is analyzed in memory and **never stored**; only the result is saved.

## How it works
1. Browser records (or loads a file) and converts it to 16 kHz mono WAV, so the server needs no ffmpeg.
2. Backend extracts 73 features (numpy/scipy): MFCC mean/std, delta-MFCC std, spectral centroid/rolloff/flatness,
   zero-crossing rate, RMS energy, pitch (autocorrelation) and voiced ratio.
3. A scikit-learn pipeline (StandardScaler + RBF SVM with probability outputs) predicts the emotion.
Without a trained model the app still reports the acoustic measurements but **does not guess an emotion**.

## Train the model (required for emotion output)
Datasets are not included. Download one yourself and train:

    cd backend
    python -m app.ml.train --dataset ravdess --data /path/to/RAVDESS      # RAVDESS (Actor_XX/*.wav)
    python -m app.ml.train --dataset cremad  --data /path/to/AudioWAV     # CREMA-D (no "surprise" class)
    python -m app.ml.train --dataset folders --data /path/to/dir          # dir/<emotion>/*.wav (TESS, own data)

RAVDESS "calm" is merged into neutral and "disgust" is skipped. With RAVDESS/CREMA-D the test set holds out whole
speakers; the dashboard reports that. Expect moderate accuracy: hand-crafted features plus an SVM are a baseline,
and acted-speech datasets transfer poorly to real conversations. A CNN on mel-spectrograms or a wav2vec2 model
is the natural next step.

## Run
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt && cp .env.example .env     # set JWT_SECRET
    uvicorn app.main:app --reload --port 8000                   # docs at /docs
    cd ../frontend && npm install && npm run dev                # http://localhost:5173
Microphone access needs `localhost` or HTTPS.

## API
POST /api/auth/register, /api/auth/login, GET /api/auth/me · POST /api/analyze (multipart WAV, field `file`) ·
GET /api/history?emotion=, DELETE /api/history/{id} · GET /api/stats · GET /api/model

## Tests
    cd backend && pytest
The API tests train a throwaway model on synthetic tones; it only exercises the code path and is not a real emotion model.

## Limits
Emotion is an estimate from voice acoustics and varies by speaker, language and culture. Do not use it for decisions
about people. Not included: rate limiting, Docker, frontend tests, migrations, streaming/real-time analysis.
