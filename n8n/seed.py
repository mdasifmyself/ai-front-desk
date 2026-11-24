"""Reset the demo data: delete every row, then add a small set of clearly marked sample records.

  python3 n8n/seed.py          # wipe + seed
Sample rows have sample=true and the console shows them with a "Sample" tag.
"""
import json, random, urllib.parse
from datetime import datetime, timedelta, timezone
from common import api, ids

I = ids()
DHAKA = timezone(timedelta(hours=6))
now = datetime.now(timezone.utc)
iso = lambda d: d.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def wipe(short):
    tid = I[f"table_{short}"]
    while True:
        rows = api("GET", f"/data-tables/{tid}/rows?limit=250")["data"]
        if not rows:
            return
        f = json.dumps({"type": "or", "filters": [{"columnName": "id", "condition": "eq", "value": r["id"]} for r in rows]})
        api("DELETE", f"/data-tables/{tid}/rows/delete?filter={urllib.parse.quote(f)}")


def add(short, rows):
    if rows:
        api("POST", f"/data-tables/{I[f'table_{short}']}/rows", {"data": rows, "returnType": "count"})


def slot(days, hour, minute=0):
    d = (now.astimezone(DHAKA) + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    while d.weekday() == 6:  # Sunday closed
        d += timedelta(days=1)
    return d.isoformat(timespec="milliseconds")


LEADS = [  # name, service, message, score, temp, urgency, stage, intent, hours_ago, source
    ("Maria Lopez", "Dental implants", "Lost a molar last year. What does an implant cost and do you offer payment plans?", 82, "hot", "this_week", "Booked", "Implant consultation, asks about payment plans", 140, "Website form"),
    ("David Chen", "Teeth whitening", "Wedding in 4 weeks, want whiter teeth.", 74, "hot", "this_week", "Booked", "Whitening before a wedding", 118, "Website form"),
    ("Aisha Rahman", "Tooth pain / emergency", "Cracked a tooth on popcorn, sharp pain when chewing.", 91, "hot", "emergency", "Booked", "Cracked tooth, needs urgent visit", 96, "Phone call (AI)"),
    ("Tom Becker", "Check-up & cleaning", "Haven't been in 3 years. Do you take MetLife?", 61, "warm", "flexible", "Contacted", "Overdue check-up, MetLife insurance", 70, "Website form"),
    ("Priya Nair", "Clear aligners", "Interested in clear aligners for my daughter (14).", 58, "warm", "flexible", "Contacted", "Aligners for a teenager", 49, "Facebook lead form"),
    ("James O'Neil", "Check-up & cleaning", "How much is a cleaning?", 32, "cold", "flexible", "Lost", "Price-only question", 30, "Website form"),
    ("Lina Haddad", "Kids' dentistry", "First visit for my 5 year old. Saturday possible?", 69, "warm", "this_week", "New", "First visit for a child, Saturday", 5, "Website form"),
]
SUMMARY = {
    "Booked": "Booked by the AI after a short call.",
    "Contacted": "AI called; caller wants to think about it. Follow-up sent.",
    "Lost": "Price shopper; not interested after hearing the price.",
    "New": "New lead, AI callback queued.",
}


def main():
    for t in ["leads", "activity", "appointments", "calls"]:
        wipe(t)
    leads, acts, appts, calls = [], [], [], []
    for k, (name, svc, msg, score, temp, urg, stage, intent, ago, src) in enumerate(LEADS):
        lid = f"L-S{k + 1:04d}"
        t0 = now - timedelta(hours=ago)
        first = name.split()[0]
        follow = f"Hi {first}, thanks for reaching out about {svc.lower()}. Would you like me to book a time for you? Ava, Lakeview Dental Clinic"
        leads.append({"lead_id": lid, "created_at": iso(t0), "updated_at": iso(t0 + timedelta(minutes=6)), "name": name,
                      "phone": f"+1 555 01{random.randint(10, 99)} {random.randint(1000, 9999)}",
                      "email": f"{first.lower()}.sample@example.com", "service": svc, "message": msg,
                      "preferred_time": "", "source": src, "stage": stage, "score": score, "temperature": temp,
                      "intent": intent, "urgency": urg, "summary": SUMMARY[stage],
                      "next_action": {"Booked": "Visit booked", "Contacted": "Follow up in 2 days", "Lost": "Close", "New": "AI callback"}[stage],
                      "followup": follow, "crm_status": "synced", "crm_id": f"C-S{k + 1:04d}", "crm_attempts": 1,
                      "crm_error": "", "sample": True})
        a = lambda s, kind, title, detail="", ch="system": acts.append(
            {"lead_id": lid, "at": iso(t0 + timedelta(seconds=s)), "kind": kind, "title": title, "detail": detail, "channel": ch, "sample": True})
        a(0, "lead", f"New lead from {src.lower() if src != 'Phone call (AI)' else 'an inbound AI call'}", f"{svc} · {msg}", "web")
        a(4, "ai", f"AI qualified the lead: {temp} · {score}/100", f"{intent}. Urgency: {urg.replace('_', ' ')}.")
        a(5, "crm", "Saved to Built-in CRM", f"Record C-S{k + 1:04d}")
        if stage == "New":
            a(6, "followup", "WhatsApp follow-up written and queued", follow, "whatsapp")
            continue
        dur = random.randint(70, 190)
        outcome = {"Booked": "Booked", "Contacted": "Question answered", "Lost": "Not interested"}[stage]
        a(45, "call", f"AI outbound call · {dur // 60}:{dur % 60:02d} · {outcome}", SUMMARY[stage], "voice")
        calls.append({"call_id": f"conv_sample_{k + 1}", "lead_id": lid, "name": name, "direction": "outbound",
                      "started_at": iso(t0 + timedelta(seconds=40)), "duration_secs": dur, "outcome": outcome,
                      "sentiment": "neutral" if stage == "Lost" else "positive", "summary": SUMMARY[stage],
                      "transcript": "[]", "tools_used": "check_availability, book_appointment" if stage == "Booked" else "",
                      "sample": True})
        if stage == "Booked":
            when = slot([1, 2, 0][k % 3] if k != 2 else 1, [10, 15, 11][k % 3], 30 if k == 1 else 0)
            appts.append({"appt_id": f"A-S{k + 1:04d}", "lead_id": lid, "name": name, "phone": leads[-1]["phone"],
                          "service": svc, "start": when, "status": "booked", "source": "AI call",
                          "created_at": iso(t0 + timedelta(seconds=120)), "sample": True})
            a(120, "appointment", "Appointment booked by AI (call)", f"{svc} · {when[:16].replace('T', ' ')}", "voice")
        else:
            a(130, "followup", "WhatsApp follow-up written after the call", follow, "whatsapp")
    add("leads", leads)
    add("activity", acts)
    add("appointments", appts)
    add("calls", calls)
    print(f"seeded {len(leads)} leads, {len(acts)} activities, {len(appts)} appointments, {len(calls)} calls")


if __name__ == "__main__":
    main()
