import { n8n, json, limited, tooMany } from "@/lib/server";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  if (limited(req, "outage", 30)) return tooMany();
  const b = await req.json().catch(() => ({}));
  const r = await n8n("console", { action: "set_outage", on: !!b.on }, 20000);
  return json(r.data, r.status);
}
