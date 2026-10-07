import { Mic, Square, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import ProbabilityBars from "../components/ProbabilityBars";
import { MAX_SECONDS, useRecorder } from "../hooks/useRecorder";
import { api, ApiError } from "../services/api";
import type { AnalysisResult } from "../types";
import { toWav16k } from "../utils/audio";
import { cap, EMOTION_COLOR } from "../utils/emotions";

type Status = "Idle" | "Listening" | "Processing" | "Finished" | "Failed";

export default function AnalyzePage() {
  const rec = useRecorder();
  const [uploaded, setUploaded] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const source: Blob | null = uploaded ?? rec.blob;
  const url = useMemo(() => (source ? URL.createObjectURL(source) : null), [source]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  const status: Status = rec.state === "recording" ? "Listening" : busy ? "Processing"
    : error || rec.state === "failed" ? "Failed" : result ? "Finished" : "Idle";

  async function analyze() {
    if (!source) return;
    setError(""); setResult(null); setBusy(true);
    try {
      const wav = await toWav16k(source);
      setResult(await api.analyze(wav, uploaded ? uploaded.name.replace(/\.[^.]+$/, "") + ".wav" : "recording.wav"));
    } catch (e) {
      setError(e instanceof ApiError || e instanceof Error ? e.message : "Analysis failed.");
    } finally { setBusy(false); }
  }

  function onFile(f: File | undefined) {
    if (!f) return;
    rec.reset(); setResult(null); setError(""); setUploaded(f);
  }
  function startRecording() { setUploaded(null); setResult(null); setError(""); void rec.start(); }

  const card = "rounded-xl bg-white p-4 shadow-sm";
  const a = result?.acoustics;
  return (
    <div className="mx-auto h-full max-w-3xl space-y-4 overflow-y-auto p-4 md:p-8">
      <div className="flex items-baseline justify-between">
        <h1 className="font-display text-2xl font-bold">Analyze a voice</h1>
        <p role="status" aria-live="polite" className="rounded-full bg-ink/10 px-3 py-1 text-xs font-medium">{status}</p>
      </div>

      <div className={`${card} flex flex-col items-center gap-3 py-8`}>
        {rec.state === "recording" ? (
          <button onClick={rec.stop} aria-label="Stop recording" className="grid h-20 w-20 place-items-center rounded-full bg-coral text-white"
            style={{ boxShadow: `0 0 0 ${6 + rec.level * 22}px rgba(214,73,91,0.2)` }}>
            <Square size={26} />
          </button>
        ) : (
          <button onClick={startRecording} disabled={rec.state === "requesting" || busy} aria-label="Start recording"
            className="grid h-20 w-20 place-items-center rounded-full bg-spruce text-mist disabled:opacity-50"><Mic size={28} /></button>
        )}
        <p className="text-sm text-ink/70">
          {rec.state === "recording" ? `Recording… ${rec.seconds}s of ${MAX_SECONDS}s` : rec.state === "requesting" ? "Waiting for microphone permission…"
            : "Tap to record, then speak naturally for a few seconds."}
        </p>
        <button onClick={() => fileRef.current?.click()} disabled={rec.state === "recording" || busy}
          className="flex items-center gap-2 text-sm underline disabled:opacity-50"><Upload size={14} /> or upload an audio file</button>
        <input ref={fileRef} type="file" accept="audio/*" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
      </div>

      {(rec.error || error) && <p role="alert" className="text-sm text-coral">{rec.error || error}</p>}

      {url && rec.state !== "recording" && (
        <div className={`${card} space-y-3`}>
          <audio controls src={url} className="w-full" />
          <button onClick={analyze} disabled={busy} className="rounded-lg bg-spruce px-5 py-2.5 font-medium text-mist disabled:opacity-50">
            {busy ? "Analyzing…" : "Analyze emotion"}
          </button>
        </div>
      )}

      {result && !result.model_available && (
        <div className="rounded-lg bg-signal/20 p-3 text-sm">{result.note} Acoustic measurements are shown below.</div>
      )}
      {result?.emotion && (
        <div className={card}>
          <p className="text-sm text-ink/60">Detected emotion</p>
          <p className="font-display text-3xl font-bold" style={{ color: EMOTION_COLOR[result.emotion] }}>{cap(result.emotion)}</p>
          <p className="mb-4 text-sm text-ink/60">Model confidence {Math.round((result.confidence ?? 0) * 100)}%. Treat this as an estimate, not a fact about how someone feels.</p>
          <ProbabilityBars probabilities={result.probabilities} />
        </div>
      )}
      {a && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {[["Length", `${a.duration_seconds}s`], ["Speech", `${a.speech_seconds}s`], ["Avg pitch", a.pitch_mean_hz ? `${a.pitch_mean_hz} Hz` : "n/a"],
            ["Pitch variation", a.pitch_mean_hz ? `${a.pitch_variation_hz} Hz` : "n/a"]].map(([k, v]) => (
            <div key={k} className={card}><p className="text-xs text-ink/60">{k}</p><p className="font-display text-xl font-bold">{v}</p></div>
          ))}
        </div>
      )}
    </div>
  );
}
