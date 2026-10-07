import type { Emotion } from "../types";
import { cap, EMOTION_COLOR } from "../utils/emotions";

export default function ProbabilityBars({ probabilities }: { probabilities: Record<string, number> }) {
  const rows = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);
  return (
    <ul className="space-y-2" aria-label="Emotion probabilities">
      {rows.map(([name, p]) => (
        <li key={name} className="flex items-center gap-3 text-sm">
          <span className="w-20">{cap(name)}</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink/10">
            <div className="h-full" style={{ width: `${p * 100}%`, background: EMOTION_COLOR[name as Emotion] ?? "#8A9A97" }} />
          </div>
          <span className="w-10 text-right tabular-nums">{Math.round(p * 100)}%</span>
        </li>
      ))}
    </ul>
  );
}
