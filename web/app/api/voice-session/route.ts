import { json, limited, tooMany, XI_KEY, AGENT_ID } from "@/lib/server";
import clinic from "@/lib/clinic.json";

export const dynamic = "force-dynamic";

const TZ = clinic.timezone;
const fmt = (d: Date, o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...o }).format(d);
const isoDay = (d: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
const clip = (v: unknown, n = 160) => String(v ?? "").replace(/[{}]/g, "").slice(0, n);

// Starts a voice session: a short-lived signed URL (the agent is private) plus the call context.
export async function POST(req: Request) {
  if (limited(req, "voice", 12)) return tooMany();
  if (!XI_KEY || !AGENT_ID) return json({ ok: false, error: "Voice is not configured." }, 500);
  const b = await req.json().catch(() => ({}));
  const outbound = b.direction === "outbound" && b.lead_id;
  const leadId = outbound ? clip(b.lead_id, 40) : "L-" + Date.now().toString(36).toUpperCase().slice(-6);
  const name = outbound ? clip(b.name, 60) : "unknown";
  const first = name.split(" ")[0];
  const service = outbound ? clip(b.service, 60) : "unknown";

  const now = new Date();
  const calendar = Array.from({ length: 14 }, (_, i) => new Date(now.getTime() + i * 86400000))
    .map((d) => `${fmt(d, { weekday: "short", day: "numeric", month: "short" })} = ${isoDay(d)}`).join(", ");
  const greeting = outbound
    ? `Hi ${first}, this is ${clinic.assistant}, the AI assistant at ${clinic.name}. You asked about ${service.toLowerCase()} on our website a moment ago. Is now a good time to talk?`
    : `Thanks for calling ${clinic.name}, this is ${clinic.assistant}, the clinic's AI assistant. How can I help you today?`;

  const r = await fetch(`https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id=${AGENT_ID}`, {
    headers: { "xi-api-key": XI_KEY }, cache: "no-store",
  });
  if (!r.ok) {
    const busy = r.status === 429 || r.status === 402;
    return json({ ok: false, error: busy ? "The voice line is busy right now. Please try again in a minute." : "Could not start the call." }, 502);
  }
  const { signed_url } = await r.json();
  return json({
    ok: true,
    signedUrl: signed_url,
    leadId,
    dynamicVariables: {
      greeting,
      call_type: outbound ? "outbound (we are calling them back about their website request)" : "inbound (they called the clinic)",
      now: `${fmt(now, { weekday: "long", day: "numeric", month: "long", year: "numeric" })}, ${fmt(now, { hour: "numeric", minute: "2-digit", hour12: true })}`,
      lead_id: leadId,
      lead_name: name,
      lead_service: service,
      lead_note: outbound ? clip(b.message, 200) || "none" : "none",
      calendar,
    },
  });
}
