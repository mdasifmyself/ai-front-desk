"""Simulated phone call: an AI 'patient' talks to the real voice agent (text only, real tools, real n8n).

  python3 tests/simulate_call.py "<patient brief>" [lead_id]
Prints the transcript with tool calls, so we can check the agent books only real free times.
"""
import json, pathlib, sys, urllib.request, urllib.error, datetime

OLD = pathlib.Path.home() / ".config/renata-assessment"
CFG = pathlib.Path.home() / ".config/crm-voice-demo"
XI = (OLD / "elevenlabs_key").read_text().strip()
AGENT = json.loads((CFG / "ids.json").read_text())["el_agent"]
brief = sys.argv[1]
lead_id = sys.argv[2] if len(sys.argv) > 2 else "L-SIM" + datetime.datetime.now().strftime("%H%M%S")

dhaka = datetime.timezone(datetime.timedelta(hours=6))
now = datetime.datetime.now(dhaka)
cal = ", ".join(f"{(now + datetime.timedelta(days=i)).strftime('%a %-d %b')} = {(now + datetime.timedelta(days=i)).date()}" for i in range(14))
dyn = {"greeting": "Thanks for calling DEMO Dental Clinic, this is Ava, the clinic's AI assistant. How can I help you today?",
       "call_type": "inbound (they called the clinic)", "now": now.strftime("%A %-d %B %Y, %-I:%M %p"), "lead_id": lead_id,
       "lead_name": "unknown", "lead_service": "unknown", "lead_note": "none", "calendar": cal}
body = {"simulation_specification": {"simulated_user_config": {"prompt": {"prompt": brief, "llm": "gpt-4o-mini", "temperature": 0.4}},
                                     "dynamic_variables": dyn}, "new_turns_limit": 16}
req = urllib.request.Request(f"https://api.elevenlabs.io/v1/convai/agents/{AGENT}/simulate-conversation", method="POST",
                             data=json.dumps(body).encode(), headers={"xi-api-key": XI, "Content-Type": "application/json"})
try:
    r = json.load(urllib.request.urlopen(req, timeout=240))
except urllib.error.HTTPError as e:
    sys.exit(f"{e.code}: {e.read().decode()[:800]}")
for t in r.get("simulated_conversation", []):
    who = "AVA " if t["role"] == "agent" else "USER"
    if t.get("message"):
        print(f"{who}: {t['message']}")
    for c in t.get("tool_calls") or []:
        print(f"   -> TOOL {c.get('tool_name')} {str(c.get('params_as_json'))[:200]}")
    for c in t.get("tool_results") or []:
        print(f"   <- RESULT {str(c.get('result_value'))[:240]}")
print("lead_id:", lead_id)
