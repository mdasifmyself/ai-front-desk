// Talks to the real voice agent over its text channel (same prompt, same tools, real n8n), no microphone needed.
//   node tests/text_call.mjs "line 1" "line 2" ...
// Each line is sent after the agent finishes its turn. Prints agent replies and tool calls.
import fs from "node:fs";
import os from "node:os";

const home = os.homedir();
const XI = fs.readFileSync(`${home}/.config/asif-demos/elevenlabs_key`, "utf8").trim();
const AGENT = JSON.parse(fs.readFileSync(`${home}/.config/asif-demos/frontdesk/ids.json`, "utf8")).el_agent;
const lines = process.argv.slice(2);
const leadId = "L-TXT" + Date.now().toString(36).toUpperCase().slice(-4);

const tz = "Asia/Dhaka";
const f = (d, o) => new Intl.DateTimeFormat("en-GB", { timeZone: tz, ...o }).format(d);
const iso = (d) => new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
const now = new Date();
const calendar = Array.from({ length: 14 }, (_, i) => new Date(now.getTime() + i * 864e5)).map((d) => `${f(d, { weekday: "short", day: "numeric", month: "short" })} = ${iso(d)}`).join(", ");

const r = await fetch(`https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id=${AGENT}`, { headers: { "xi-api-key": XI } });
const { signed_url } = await r.json();
const ws = new WebSocket(signed_url);
let i = 0, timer;
const next = () => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (i < lines.length) { console.log(`USER: ${lines[i]}`); ws.send(JSON.stringify({ type: "user_message", text: lines[i++] })); }
    else { console.log(`(done) lead_id: ${leadId}`); ws.close(); }
  }, 2500);
};
ws.onopen = () => ws.send(JSON.stringify({
  type: "conversation_initiation_client_data",
  conversation_config_override: { conversation: { text_only: true } },
  dynamic_variables: {
    greeting: "Thanks for calling Lakeview Dental Clinic, this is Ava, the clinic's AI assistant. How can I help you today?",
    call_type: "inbound (they called the clinic)", now: `${f(now, { weekday: "long", day: "numeric", month: "long", year: "numeric" })}, ${f(now, { hour: "numeric", minute: "2-digit", hour12: true })}`,
    lead_id: leadId, lead_name: "unknown", lead_service: "unknown", lead_note: "none", calendar,
  },
}));
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.type === "ping") return ws.send(JSON.stringify({ type: "pong", event_id: m.ping_event.event_id }));
  if (m.type === "conversation_initiation_metadata") console.log("conversation:", m.conversation_initiation_metadata_event.conversation_id);
  if (m.type === "agent_response") { console.log(`AVA : ${m.agent_response_event.agent_response}`); next(); }
  if (m.type === "agent_tool_response") console.log(`   -> TOOL ${m.agent_tool_response.tool_name}${m.agent_tool_response.is_error ? " (ERROR)" : ""}`);
};
ws.onclose = (e) => { console.log("closed", e.code, e.reason || ""); process.exit(0); };
setTimeout(() => { console.log("timeout"); process.exit(1); }, 150000);
