import { n8n, json, limited, tooMany } from "@/lib/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  if (limited(req, "comments", 20)) return tooMany();
  const b = await req.json().catch(() => ({}));
  const comments = (Array.isArray(b.comments) ? b.comments : []).slice(0, 12)
    .map((c: { author?: string; text?: string }) => ({ author: String(c.author || "").slice(0, 40), text: String(c.text || "").slice(0, 400) }));
  const r = await n8n("comments", { comments }, 45000);
  return json(r.data, r.status);
}
