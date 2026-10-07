import { Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import type { Emotion, HistoryItem } from "../types";
import { cap, EMOTION_COLOR, EMOTIONS } from "../utils/emotions";

export default function HistoryPage() {
  const [rows, setRows] = useState<HistoryItem[]>([]);
  const [filter, setFilter] = useState<Emotion | "all">("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setRows(await api.history(filter === "all" ? undefined : filter)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Could not load history."); }
    finally { setLoading(false); }
  }, [filter]);
  useEffect(() => { load(); }, [load]);

  async function remove(id: number) {
    try { await api.deleteAnalysis(id); setRows((r) => r.filter((x) => x.id !== id)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Could not delete."); }
  }

  return (
    <div className="mx-auto h-full max-w-3xl space-y-4 overflow-y-auto p-4 md:p-8">
      <h1 className="font-display text-2xl font-bold">History</h1>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by emotion">
        {(["all", ...EMOTIONS] as const).map((f) => (
          <button key={f} onClick={() => setFilter(f)} aria-pressed={filter === f}
            className={`rounded-full px-4 py-1.5 text-sm ${filter === f ? "bg-spruce text-mist" : "bg-white"}`}>{cap(f)}</button>
        ))}
      </div>
      {error && <p role="alert" className="text-sm text-coral">{error}</p>}
      {loading ? <p className="text-ink/60">Loading…</p> : rows.length === 0 ? (
        <p className="text-ink/60">No analyses yet. Recorded results appear here. Audio itself is not saved.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.id} className="flex items-center gap-3 rounded-xl bg-white p-3 shadow-sm">
              <span className="rounded-full px-3 py-1 text-xs font-medium text-white" style={{ background: EMOTION_COLOR[r.emotion] }}>{cap(r.emotion)}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">{r.filename} · {Math.round(r.confidence * 100)}% · {r.duration_seconds}s</p>
                <time className="text-xs text-ink/50">{new Date(r.created_at).toLocaleString()}</time>
              </div>
              <button onClick={() => remove(r.id)} aria-label="Delete result" className="p-1 opacity-60 hover:opacity-100"><Trash2 size={16} /></button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
