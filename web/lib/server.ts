// Server-only helpers: every call to n8n or ElevenLabs goes through here, so no key reaches the browser.
import "server-only";

const N8N = process.env.N8N_WEBHOOK_BASE || "";
const KEY = process.env.DEMO_WEBHOOK_KEY || "";
export const XI_KEY = process.env.ELEVENLABS_API_KEY || "";
export const AGENT_ID = process.env.ELEVENLABS_AGENT_ID || "";

export async function n8n(path: string, body: unknown, timeoutMs = 30000) {
  try {
    const r = await fetch(`${N8N}/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Demo-Key": KEY },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    const text = await r.text();
    try {
      return { status: r.status, data: JSON.parse(text) };
    } catch {
      return { status: 502, data: { ok: false, error: "The automation server sent an unreadable reply." } };
    }
  } catch (e) {
    console.error("n8n call failed:", path, (e as Error)?.message, (e as { cause?: unknown })?.cause);
    return { status: 504, data: { ok: false, error: "The automation server is busy. Please try again." } };
  }
}

// Best-effort limit per visitor and route (resets when the server instance restarts).
const hits = new Map<string, number[]>();
export function limited(req: Request, route: string, max: number, windowMs = 10 * 60 * 1000) {
  const ip = (req.headers.get("x-forwarded-for") || "local").split(",")[0].trim();
  const key = `${route}:${ip}`;
  const now = Date.now();
  const list = (hits.get(key) || []).filter((t) => now - t < windowMs);
  list.push(now);
  hits.set(key, list);
  return list.length > max;
}

export function json(data: unknown, status = 200) {
  return Response.json(data, { status, headers: { "Cache-Control": "no-store" } });
}

export const tooMany = () => json({ ok: false, error: "Too many tries from this device. Please wait a few minutes." }, 429);
