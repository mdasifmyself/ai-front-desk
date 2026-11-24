import { XI_KEY } from "@/lib/server";

export const dynamic = "force-dynamic";

// Streams a call recording from ElevenLabs without exposing the API key.
export async function GET(req: Request) {
  const id = new URL(req.url).searchParams.get("id") || "";
  if (!/^conv_[A-Za-z0-9]+$/.test(id)) return new Response("Not found", { status: 404 });
  const r = await fetch(`https://api.elevenlabs.io/v1/convai/conversations/${id}/audio`, { headers: { "xi-api-key": XI_KEY }, cache: "no-store" });
  if (!r.ok || !r.body) return new Response("Recording not ready yet", { status: 404 });
  return new Response(r.body, { headers: { "Content-Type": r.headers.get("content-type") || "audio/mpeg", "Cache-Control": "private, max-age=3600" } });
}
