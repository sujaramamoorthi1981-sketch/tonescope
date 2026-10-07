export interface User { id: number; name: string; email: string; created_at: string }
export type Emotion = "happy" | "sad" | "angry" | "fear" | "surprise" | "neutral";
export interface Acoustics {
  duration_seconds: number; speech_seconds: number; speech_activity: number;
  pitch_mean_hz: number; pitch_variation_hz: number; voiced_ratio: number; brightness_hz: number;
}
export interface AnalysisResult {
  id: number | null; model_available: boolean; emotion: Emotion | null; confidence: number | null;
  probabilities: Record<string, number>; acoustics: Acoustics; note: string | null;
  filename?: string; created_at?: string;
}
export interface HistoryItem {
  id: number; filename: string; duration_seconds: number; emotion: Emotion; confidence: number; created_at: string;
}
export interface Stats {
  total: number; average_confidence: number; by_emotion: Record<string, number>;
  per_day: { date: string; count: number }[];
}
export interface ModelInfo {
  available: boolean; note: string | null;
  metrics: { accuracy: number; macro_f1: number; dataset_size: number; test_size: number; classes: string[]; speaker_independent_split: boolean } | null;
}
