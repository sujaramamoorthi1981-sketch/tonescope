import type { Emotion } from "../types";

export const EMOTIONS: Emotion[] = ["happy", "sad", "angry", "fear", "surprise", "neutral"];
export const EMOTION_COLOR: Record<Emotion, string> = {
  happy: "#E0A030", sad: "#5B7DB1", angry: "#D6495B", fear: "#7A5C8E", surprise: "#2F9E9E", neutral: "#8A9A97",
};
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
