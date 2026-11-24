import { n8n, json, limited, tooMany, XI_KEY } from "@/lib/server";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

type Turn = { role: string; message?: string | null; tool_calls?: { tool_name?: string }[] };

// After a call: take the official transcript from ElevenLabs (falls back to the one the browser saw),
// then hand it to n8n workflow 03, which writes the CRM note, call log and follow-up.
export async function POST(req: Request) {
  if (limited(req, "call-ended", 20)) return tooMany();
  const b = await req.json().catch(() => ({}));
  const id = String(b.conversation_id || "");
  let transcript: { role: string; message: string }[] = (Array.isArray(b.transcript) ? b.transcript : [])
    .slice(0, 80).map((t: Turn) => ({ role: t.role === "agent" ? "agent" : "user", message: String(t.message || "").slice(0, 600) }));
  let tools: string[] = (Array.isArray(b.tools) ? b.tools : []).map(String).slice(0, 30);
  let duration = Number(b.duration_secs || 0);

  if (/^conv_[A-Za-z0-9]+$/.test(id) && XI_KEY) {
    for (let i = 0; i < 6; i++) {
      const r = await fetch(`https://api.elevenlabs.io/v1/convai/conversations/${id}`, { headers: { "xi-api-key": XI_KEY }, cache: "no-store" });
      if (r.ok) {
        const c = await r.json();
        if (Array.isArray(c.transcript) && c.transcript.length) {
          const turns = c.transcript as Turn[];
          transcript = turns.filter((t) => t.message).map((t) => ({ role: t.role === "agent" ? "agent" : "user", message: String(t.message).slice(0, 600) }));
          tools = turns.flatMap((t) => (t.tool_calls || []).map((x) => String(x.tool_name || ""))).filter(Boolean);
          duration = Number(c.metadata?.call_duration_secs || duration);
        }
        if (c.status === "done" || c.status === "failed") break;
      }
      await new Promise((res) => setTimeout(res, 1500));
    }
  }

  const r = await n8n("call-ended", {
    conversation_id: id, lead_id: String(b.lead_id || "").slice(0, 40), direction: b.direction === "outbound" ? "outbound" : "inbound",
    started_at: String(b.started_at || ""), duration_secs: duration, transcript, tools: Array.from(new Set(tools)),
  }, 45000);
  return json(r.data, r.status);
}
