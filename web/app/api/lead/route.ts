import { n8n, json, limited, tooMany } from "@/lib/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  if (limited(req, "lead", 20)) return tooMany();
  const b = await req.json().catch(() => ({}));
  const pick = (k: string) => String(b[k] ?? "").slice(0, 500);
  const r = await n8n("lead", {
    name: pick("name"), phone: pick("phone"), email: pick("email"), service: pick("service"),
    message: pick("message"), preferred_time: pick("preferred_time"), source: "Website form",
  });
  return json(r.data, r.status);
}
