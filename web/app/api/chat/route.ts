import { n8n, json, limited, tooMany } from "@/lib/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  if (limited(req, "chat", 60)) return tooMany();
  const b = await req.json().catch(() => ({}));
  const history = Array.isArray(b.history) ? b.history.slice(-12) : [];
  const r = await n8n("chat", { lead_id: String(b.lead_id || "").slice(0, 40), message: String(b.message || "").slice(0, 600), history }, 45000);
  return json(r.data, r.status);
}
