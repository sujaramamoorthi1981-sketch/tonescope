import { useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import type { ModelInfo, Stats } from "../types";
import { cap, EMOTION_COLOR, EMOTIONS } from "../utils/emotions";

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setError(e instanceof ApiError ? e.message : "Could not load stats."));
    api.model().then(setInfo).catch(() => {});
  }, []);

  const card = "rounded-xl bg-white p-4 shadow-sm";
  const maxEmotion = Math.max(1, ...Object.values(stats?.by_emotion ?? {}));
  const maxDay = Math.max(1, ...(stats?.per_day.map((d) => d.count) ?? [1]));
  return (
    <div className="mx-auto h-full max-w-4xl space-y-4 overflow-y-auto p-4 md:p-8">
      <h1 className="font-display text-2xl font-bold">Dashboard</h1>
      {error && <p role="alert" className="text-sm text-coral">{error}</p>}
      {stats && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className={card}><p className="text-sm text-ink/60">Recordings analyzed</p><p className="font-display text-3xl font-bold">{stats.total}</p></div>
            <div className={card}><p className="text-sm text-ink/60">Average confidence</p><p className="font-display text-3xl font-bold">{Math.round(stats.average_confidence * 100)}%</p></div>
          </div>
          <div className={card}>
            <h2 className="mb-3 font-medium">Emotion distribution</h2>
            <ul className="space-y-2">
              {EMOTIONS.map((e) => (
                <li key={e} className="flex items-center gap-3 text-sm">
                  <span className="w-20">{cap(e)}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink/10">
                    <div className="h-full" style={{ width: `${((stats.by_emotion[e] ?? 0) / maxEmotion) * 100}%`, background: EMOTION_COLOR[e] }} />
                  </div>
                  <span className="w-8 text-right tabular-nums">{stats.by_emotion[e] ?? 0}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className={card}>
            <h2 className="mb-3 font-medium">Last 14 days</h2>
            {stats.per_day.length === 0 ? <p className="text-sm text-ink/60">No recordings in this period.</p> : (
              <div className="flex h-36 items-end gap-2">
                {stats.per_day.map((d) => (
                  <div key={d.date} className="flex flex-1 flex-col items-center gap-1" title={`${d.date}: ${d.count}`}>
                    <div className="flex w-full flex-1 items-end"><div className="w-full bg-spruce" style={{ height: `${(d.count / maxDay) * 100}%` }} /></div>
                    <span className="text-[10px] text-ink/50">{d.date.slice(5)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
      {info && (
        <div className={card}>
          <h2 className="mb-1 font-medium">Model</h2>
          {info.metrics ? (
            <p className="text-sm">Trained on {info.metrics.dataset_size} clips ({info.metrics.classes.join(", ")}). Held-out test accuracy {info.metrics.accuracy}, macro F1 {info.metrics.macro_f1}.
              {info.metrics.speaker_independent_split ? " Test speakers were not in the training set." : " Test split was not speaker-independent, so scores may be optimistic."}</p>
          ) : <p className="text-sm">{info.note}</p>}
        </div>
      )}
    </div>
  );
}
