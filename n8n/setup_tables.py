"""Create the DEMO Dental data tables in n8n (once). Safe to re-run: existing tables are kept."""
from common import api, ids, save_ids

S, N, B = "string", "number", "boolean"
TABLES = {
    "leads": [("lead_id", S), ("created_at", S), ("updated_at", S), ("name", S), ("phone", S), ("email", S),
              ("service", S), ("message", S), ("preferred_time", S), ("source", S), ("stage", S),
              ("score", N), ("temperature", S), ("intent", S), ("urgency", S), ("summary", S),
              ("next_action", S), ("followup", S), ("crm_status", S), ("crm_id", S), ("crm_attempts", N),
              ("crm_error", S), ("sample", B)],
    "activity": [("lead_id", S), ("at", S), ("kind", S), ("title", S), ("detail", S), ("channel", S),
                 ("sample", B)],
    "appointments": [("appt_id", S), ("lead_id", S), ("name", S), ("phone", S), ("service", S), ("start", S),
                     ("status", S), ("source", S), ("created_at", S), ("sample", B)],
    "calls": [("call_id", S), ("lead_id", S), ("name", S), ("direction", S), ("started_at", S),
              ("duration_secs", N), ("outcome", S), ("sentiment", S), ("summary", S), ("transcript", S),
              ("tools_used", S), ("sample", B)],
    "settings": [("key", S), ("value", S)],
}

d = ids()
existing = {t["name"]: t["id"] for t in api("GET", "/data-tables?limit=100")["data"]}
for short, cols in TABLES.items():
    name = f"DEMO Dental {short}"
    if name in existing:
        d[f"table_{short}"] = existing[name]
        print("kept", name)
        continue
    t = api("POST", "/data-tables", {"name": name, "columns": [{"name": c, "type": ty} for c, ty in cols]})
    d[f"table_{short}"] = t["id"]
    print("created", name)
save_ids(d)
