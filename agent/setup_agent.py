"""Create or update the ElevenLabs voice agent (AI receptionist) and its server tools.

  python3 agent/setup_agent.py

Tools are webhooks into n8n workflow 02 (/webhook/demo-dental/tool?name=<tool>), authenticated with the
demo header key. Dynamic variables (lead id, caller name, today's calendar) are sent by the website when
a call starts. IDs are saved to ~/.config/asif-demos/frontdesk/ids.json; secrets are never printed.
"""
import json, pathlib, sys, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
PROJ = ROOT.parent
SHARED = pathlib.Path.home() / ".config/asif-demos"
CFG = SHARED / "frontdesk"
XI = (SHARED / "elevenlabs_key").read_text().strip()
HOOK_BASE = (SHARED / "webhook_base").read_text().strip()   # the public https address, ends in /webhook
KEY = (CFG / "webhook_secret").read_text().strip()
CLINIC = json.loads((PROJ / "clinic.json").read_text())
IDS = json.loads((CFG / "ids.json").read_text())
LLM = "gpt-4.1"
VOICE = "hpp4J3VqNfWAUOO0d1Us"  # Bella: professional, bright, warm (ElevenLabs premade)


def el(method, path, body=None):
    req = urllib.request.Request("https://api.elevenlabs.io" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": XI, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs {method} {path} -> {e.code}: {e.read().decode()[:900]}")


def p(desc, typ="string", **kw):
    return {"type": typ, "description": desc, **kw}


LEAD = {"type": "string", "description": "", "dynamic_variable": "lead_id"}
TOOLS = {
    "check_availability": ("Get the clinic's real free appointment times for one day. Always call this before offering any time.",
                           {"date": p("Day to check, as YYYY-MM-DD. Use the calendar in the prompt to convert words like 'tomorrow' or 'Thursday'."),
                            "time_of_day": p("Preferred part of the day", enum=["any", "morning", "afternoon"])}, ["date"]),
    "book_appointment": ("Book a visit. Only after the caller chose a free time and confirmed name, service, day and time.",
                         {"date": p("YYYY-MM-DD"), "time": p("24-hour time HH:MM, e.g. 15:30"),
                          "service": p("Service, e.g. Check-up & cleaning, Teeth whitening, Tooth pain / emergency, Dental implants"),
                          "name": p("Patient's full name"), "phone": p("Patient's phone number, digits only")},
                         ["date", "time", "service", "name"]),
    "find_booking": ("Find the caller's upcoming bookings (for changes or cancellations).",
                     {"phone": p("Caller's phone number if they give one; otherwise empty")}, []),
    "cancel_appointment": ("Cancel one booking by its appointment id from find_booking. Confirm with the caller first.",
                           {"appointment_id": p("Appointment id, e.g. A-0D7PCPW")}, ["appointment_id"]),
    "save_caller_details": ("Save or update the caller's details in the CRM as soon as you learn them.",
                            {"name": p("Full name"), "phone": p("Phone number"), "email": p("Email, if given"),
                             "service": p("What they need"), "notes": p("Short note for the front desk"),
                             "urgency": p("How urgent", enum=["emergency", "this_week", "flexible"])}, ["name"]),
    "request_callback": ("Create a callback task for a human team member: unknown answers, insurance not on the list, complaints, or the caller asks for a person.",
                         {"reason": p("What the team must call back about, one sentence"),
                          "urgency": p("Urgency", enum=["emergency", "this_week", "flexible"])}, ["reason"]),
}


def tool_config(name):
    desc, props, req = TOOLS[name]
    props = dict(props, lead_id=LEAD, channel={"type": "string", "description": "", "constant_value": "voice"})
    return {"type": "webhook", "name": name, "description": desc, "response_timeout_secs": 20,
            "api_schema": {"url": f"{HOOK_BASE}/demo-dental/tool?name={name}", "method": "POST",
                           "request_headers": {"X-Demo-Key": KEY},
                           "request_body_schema": {"type": "object", "description": f"Arguments for {name}",
                                                   "properties": props, "required": req}}}


def prompt():
    services = "\n".join(f"- {s['name']}: {s['price']}" for s in CLINIC["services"])
    dentists = "\n".join(f"- {d}" for d in CLINIC["dentists"])
    policies = "\n".join(f"- {x}" for x in CLINIC["policies"])
    return f"""# Who you are
You are {CLINIC['assistant']}, the AI receptionist of {CLINIC['name']}. You are on a live phone call. You say you are the clinic's AI assistant if asked.
Call type: {{{{call_type}}}}. Now: {{{{now}}}}.
Caller on file: {{{{lead_name}}}} (lead {{{{lead_id}}}}). They asked about: {{{{lead_service}}}}. Their note: {{{{lead_note}}}}.

# How you speak
- Short, warm, natural sentences. One question at a time. Never read out ids, links or long lists.
- Say times like "ten thirty in the morning". Say prices like "two hundred ninety-nine dollars".
- If the caller is outbound (we are calling them back about their website request), confirm it is a good time, then help them book.

# What you may say (facts)
Answer ONLY from this fact sheet. If the answer is not here (for example an insurance plan that is not listed), say "I'll have the team confirm that and call you back" and call request_callback in the same turn, so a real task is created.
Never give a diagnosis, medication advice or a price that is not listed.
Address: {CLINIC['address']}. Phone: {CLINIC['phone']}.
Hours: {CLINIC['hours_text']}.
Services and prices:
{services}
Dentists:
{dentists}
Insurance: {CLINIC['insurance']}
Policies:
{policies}
Emergencies: {CLINIC['emergency_rule']}

# Booking (use the tools, never guess)
Calendar for converting days to dates: {{{{calendar}}}}
1. Ask what they need and which day suits them. Call check_availability for that day. Offer two or three of the returned times only.
2. Before booking, make sure you have the full name and phone number (use the number on file if the caller confirms it). Call save_caller_details once you know the name.
3. Read back name, service, day and time in one sentence and ask "Shall I book that?". Call book_appointment ONLY after the caller says yes in their next reply; never in the same turn as the read-back. If it says the time is taken, offer the alternatives it returns. Never say a visit is booked or reserved until book_appointment returned booked: true.
4. To move or cancel: find_booking, confirm which one, cancel_appointment, then offer a new time.
5. Pain or swelling: offer the earliest slot today or tomorrow. Danger signs in the emergency rule: tell them to call 911 now.

# Ending
When the caller is done, thank them, say goodbye and end the call."""


def main():
    tool_ids = IDS.get("el_tools", {})
    for name in TOOLS:
        cfg = {"tool_config": tool_config(name)}
        if name in tool_ids:
            el("PATCH", f"/v1/convai/tools/{tool_ids[name]}", cfg)
        else:
            tool_ids[name] = el("POST", "/v1/convai/tools", cfg)["id"]
    IDS["el_tools"] = tool_ids
    conv = {
        "agent": {
            "first_message": "{{greeting}}",
            "language": "en",
            "dynamic_variables": {"dynamic_variable_placeholders": {
                "greeting": f"Thanks for calling {CLINIC['name']}, this is {CLINIC['assistant']}, the clinic's AI assistant. How can I help you today?",
                "call_type": "inbound", "now": "Monday 2 November 2026, 4:00 PM", "lead_id": "L-TEST", "lead_name": "unknown",
                "lead_service": "unknown", "lead_note": "none", "calendar": "Mon 2 Nov = 2026-11-02"}},
            "prompt": {"prompt": prompt(), "llm": LLM, "temperature": 0.3, "tool_ids": list(tool_ids.values()),
                       "built_in_tools": {"end_call": {"name": "end_call", "description": "End the call when the caller is done.",
                                                       "params": {"system_tool_type": "end_call"}}}},
        },
        "tts": {"voice_id": VOICE, "model_id": "eleven_flash_v2", "stability": 0.55, "similarity_boost": 0.8, "speed": 1.03},
        "conversation": {"max_duration_seconds": 180,
                         "client_events": ["audio", "interruption", "user_transcript", "agent_response",
                                           "agent_response_correction", "agent_tool_response"]},
    }
    platform = {"auth": {"enable_auth": True},
                "call_limits": {"agent_concurrency_limit": 3, "daily_limit": 30},
                "overrides": {"conversation_config_override": {"conversation": {"text_only": True}}}}
    body = {"name": "Front Desk · AI receptionist", "conversation_config": conv, "platform_settings": platform, "tags": ["demo"]}
    if IDS.get("el_agent"):
        el("PATCH", f"/v1/convai/agents/{IDS['el_agent']}", body)
        print("updated agent")
    else:
        IDS["el_agent"] = el("POST", "/v1/convai/agents/create", body)["agent_id"]
        print("created agent")
    (CFG / "ids.json").write_text(json.dumps(IDS, indent=2))
    print("tools:", ", ".join(tool_ids))


if __name__ == "__main__":
    main()
