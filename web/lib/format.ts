import clinic from "./clinic.json";

const TZ = clinic.timezone;

export function ago(iso: string, now = Date.now()) {
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  const d = Math.round(s / 86400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}

export const dayTime = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hour12: true }).format(new Date(iso));
export const time = (iso: string) =>
  new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" }).format(new Date(iso));
export const dayLabel = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" }).format(new Date(iso));
export const dayKey = (iso: string) =>
  new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(iso));

export const mmss = (secs: number) => `${Math.floor(secs / 60)}:${String(Math.round(secs) % 60).padStart(2, "0")}`;
export const initials = (name: string) => (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("") || "?";
export const displayName = (name: string) => name?.trim() || "New contact";
export const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);
