import { n8n, json } from "@/lib/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const r = await n8n("console", { action: "snapshot" }, 20000);
  return json(r.data, r.status);
}
