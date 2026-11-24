"""Builds and deploys the Front Desk n8n workflows (create or update by name, then activate).

  python3 n8n/build.py

Rules:
- The original "Leave Policy Assistant" workflows are only READ. Workflow 04 (chat agent) starts as a
  complete copy of the Answer Engine, saved under a new name and a new webhook path, then customised.
- All secrets live in ~/.config/asif-demos (never printed, never in the web code).
"""
import json, pathlib, secrets, uuid
from common import api, ids, save_ids, CFG, OPENAI_CRED, MODEL, PREFIX, ROOT

PROJ = ROOT.parent
CLINIC = json.loads((PROJ / "clinic.json").read_text())
I = ids()
HUBSPOT_TOKEN = (CFG / "hubspot_token.txt").read_text().strip() if (CFG / "hubspot_token.txt").exists() else ""
HUBSPOT = bool(HUBSPOT_TOKEN)

LEAD_COLS = ["lead_id", "created_at", "updated_at", "name", "phone", "email", "service", "message",
             "preferred_time", "source", "stage", "score", "temperature", "intent", "urgency", "summary",
             "next_action", "followup", "crm_status", "crm_id", "crm_attempts", "crm_error", "sample"]
NUM = {"score", "crm_attempts", "duration_secs"}
BOOL = {"sample"}


# ---------- credentials ----------
def webhook_cred():
    if "cred_webhook" in I:
        return I["cred_webhook"]
    secret = secrets.token_urlsafe(32)
    (CFG / "webhook_secret").write_text(secret)
    (CFG / "webhook_secret").chmod(0o600)
    c = api("POST", "/credentials", {"name": "Front Desk | webhook key", "type": "httpHeaderAuth",
                                     "data": {"name": "X-Demo-Key", "value": secret}})
    I["cred_webhook"] = {"id": c["id"], "name": c["name"]}
    save_ids(I)
    return I["cred_webhook"]


def hubspot_cred():
    if not HUBSPOT:
        return None
    if "cred_hubspot" in I:
        return I["cred_hubspot"]
    c = api("POST", "/credentials", {"name": "Front Desk | HubSpot", "type": "httpHeaderAuth",
                                     "data": {"name": "Authorization", "value": "Bearer " + HUBSPOT_TOKEN}})
    I["cred_hubspot"] = {"id": c["id"], "name": c["name"]}
    save_ids(I)
    return I["cred_hubspot"]


# ---------- node helpers ----------
def node(name, typ, params, pos, tv=1, **extra):
    n = {"id": str(uuid.uuid4()), "name": name, "type": typ, "typeVersion": tv, "position": list(pos),
         "parameters": params}
    n.update(extra)
    return n


def note(text, pos, w=300, h=200):
    return node(f"Note {uuid.uuid4().hex[:4]}", "n8n-nodes-base.stickyNote", {"content": text, "width": w, "height": h}, pos)


def code(name, js, pos, **extra):
    return node(name, "n8n-nodes-base.code", {"jsCode": js}, pos, tv=2, **extra)


def webhook(path, pos, name="Webhook"):
    return node(name, "n8n-nodes-base.webhook",
                {"httpMethod": "POST", "path": path, "authentication": "headerAuth", "responseMode": "responseNode",
                 "options": {}}, pos, tv=2, webhookId=str(uuid.uuid4()), credentials={"httpHeaderAuth": webhook_cred()})


def respond(name, expr, pos, status=200):
    return node(name, "n8n-nodes-base.respondToWebhook",
                {"respondWith": "json", "responseBody": expr, "options": {"responseCode": status}}, pos, tv=1.1)


def if_true(name, expr, pos):
    return node(name, "n8n-nodes-base.if", {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
        "conditions": [{"id": str(uuid.uuid4()), "leftValue": expr, "rightValue": "",
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "options": {}}, pos, tv=2.2)


def table(short):
    return {"__rl": True, "mode": "id", "value": I[f"table_{short}"], "cachedResultName": f"Front Desk {short}"}


def dt_get(name, short, pos, key=None, value=None):
    p = {"resource": "row", "operation": "get", "dataTableId": table(short), "returnAll": True}
    if key:
        p.update({"matchType": "allConditions", "filters": {"conditions": [{"keyName": key, "condition": "eq", "keyValue": value}]}})
    return node(name, "n8n-nodes-base.dataTable", p, pos, tv=1.1, alwaysOutputData=True, executeOnce=True)


def dt_insert(name, short, pos):
    return node(name, "n8n-nodes-base.dataTable",
                {"resource": "row", "operation": "insert", "dataTableId": table(short),
                 "columns": {"mappingMode": "autoMapInputData", "value": None, "matchingColumns": [], "schema": []}},
                pos, tv=1.1)


def schema(cols):
    return [{"id": c, "displayName": c, "required": False, "defaultMatch": False, "display": True,
             "type": "number" if c in NUM else "boolean" if c in BOOL else "string", "canBeUsedToMatch": True}
            for c in cols]


def dt_update(name, short, pos, key, value_expr, cols):
    return node(name, "n8n-nodes-base.dataTable",
                {"resource": "row", "operation": "update", "dataTableId": table(short), "matchType": "allConditions",
                 "filters": {"conditions": [{"keyName": key, "condition": "eq", "keyValue": value_expr}]},
                 "columns": {"mappingMode": "defineBelow", "matchingColumns": [], "schema": schema(cols),
                             "value": {c: "={{ $json.%s }}" % c for c in cols}}}, pos, tv=1.1)


def run_sub(name, wf_key, pos, each=False):
    return node(name, "n8n-nodes-base.executeWorkflow",
                {"workflowId": {"__rl": True, "value": I[wf_key], "mode": "id"},
                 "workflowInputs": {"mappingMode": "defineBelow", "value": {}, "matchingColumns": [], "schema": [],
                                    "attemptToConvertTypes": False, "convertFieldsToString": True},
                 "mode": "each" if each else "once", "options": {"waitForSubWorkflow": True}}, pos, tv=1.2)


def openai(name, pos):
    return node(name, "n8n-nodes-base.httpRequest",
                {"method": "POST", "url": "https://api.openai.com/v1/responses",
                 "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
                 "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
                 "options": {"timeout": 45000}}, pos, tv=4.2, credentials={"openAiApi": OPENAI_CRED},
                onError="continueErrorOutput", retryOnFail=True, maxTries=2, waitBetweenTries=1000)


def trigger_sub(pos):
    return node("Start", "n8n-nodes-base.executeWorkflowTrigger", {"inputSource": "passthrough"}, pos, tv=1.1)


def link(conns, a, b, out=0, inp=0):
    c = conns.setdefault(a, {"main": []})["main"]
    while len(c) <= out:
        c.append([])
    c[out].append({"node": b, "type": "main", "index": inp})


def chain(conns, *names):
    for a, b in zip(names, names[1:]):
        link(conns, a, b)


# ---------- shared JavaScript ----------
CLINIC_JS = r"""
const CLINIC = __CLINIC__;
const TZ = CLINIC.timezone;
const nowLocal = () => DateTime.now().setZone(TZ);
const fmtDay = d => d.toFormat('cccc d LLLL');
const fmtTime = d => d.toFormat('h:mm a');
const keyOf = d => d.toFormat("yyyy-LL-dd'T'HH:mm");
const apptKey = iso => keyOf(DateTime.fromISO(iso, { setZone: true }).setZone(TZ));
const takenSet = appts => new Set(appts.filter(a => a.status === 'booked' && a.start).map(a => apptKey(a.start)));
function daySlots(dateStr, taken) {
  const d = DateTime.fromISO(String(dateStr || ''), { zone: TZ }).startOf('day');
  if (!d.isValid) return { error: 'bad_date' };
  const h = CLINIC.open[String(d.weekday)];
  if (!h) return { day: d, closed: true, slots: [] };
  const earliest = nowLocal().plus({ minutes: 30 });
  const slots = [];
  for (let t = d.set({ hour: h[0] }); t < d.set({ hour: h[1] }); t = t.plus({ minutes: CLINIC.slot_minutes })) {
    if (h[1] > CLINIC.lunch[1] && t.hour >= CLINIC.lunch[0] && t.hour < CLINIC.lunch[1]) continue;
    if (t < earliest || taken.has(keyOf(t))) continue;
    slots.push(t);
  }
  return { day: d, closed: false, slots };
}
function pick(slots, part) {
  let s = slots;
  if (part === 'morning') s = s.filter(t => t.hour < 12);
  if (part === 'afternoon') s = s.filter(t => t.hour >= 12);
  if (s.length <= 6) return s;
  const step = s.length / 6;
  return [0, 1, 2, 3, 4, 5].map(i => s[Math.floor(i * step)]);
}
function nextOpen(fromDay, taken, n) {
  const out = [];
  for (let i = 1; i <= 14 && out.length < n; i++) {
    const r = daySlots(fromDay.plus({ days: i }).toISODate(), taken);
    if (r.slots && r.slots.length) out.push({ date: r.day.toISODate(), day: fmtDay(r.day), times: pick(r.slots, 'any').slice(0, 3).map(fmtTime) });
  }
  return out;
}
function parseTime(s) {
  const m = String(s || '').trim().toLowerCase().replace(/\./g, '').match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/);
  if (!m) return null;
  let h = +m[1]; const mi = +(m[2] || 0);
  if (m[3] === 'pm' && h < 12) h += 12;
  if (m[3] === 'am' && h === 12) h = 0;
  return h > 23 || mi > 59 ? null : { h, mi };
}
const newId = p => p + '-' + Date.now().toString(36).toUpperCase().slice(-5) + Math.random().toString(36).slice(2, 4).toUpperCase();
const clean = o => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== ''));
function factSheet() {
  return [
    `Clinic: ${CLINIC.name}. Address: ${CLINIC.address}. Phone: ${CLINIC.phone}.`,
    `Opening hours: ${CLINIC.hours_text}.`,
    'Services and prices:', ...CLINIC.services.map(s => `- ${s.name}: ${s.price}`),
    'Dentists:', ...CLINIC.dentists.map(d => `- ${d}`),
    `Insurance: ${CLINIC.insurance}`,
    'Policies:', ...CLINIC.policies.map(p => `- ${p}`),
    `Emergencies: ${CLINIC.emergency_rule}`,
  ].join('\n');
}
function outText(r) {
  if (r && typeof r.output_text === 'string') return r.output_text;
  for (const o of (r && r.output) || []) if (o.type === 'message') for (const c of o.content || []) if (c.type === 'output_text') return c.text;
  return '';
}
"""


def js(src):
    return src.replace("__CLINIC_JS__", CLINIC_JS).replace("__CLINIC__", json.dumps(CLINIC)) \
        .replace("__MODEL__", json.dumps(MODEL)).replace("__LEAD_COLS__", json.dumps(LEAD_COLS)) \
        .replace("__HUBSPOT__", "true" if HUBSPOT else "false")


SETTINGS = {"executionOrder": "v1", "saveDataSuccessExecution": "all", "saveDataErrorExecution": "all",
            "saveManualExecutions": True, "executionTimeout": 120, "callerPolicy": "workflowsFromSameOwner"}


def deploy(key, name, nodes, conns, activate=True, settings=None):
    st = dict(SETTINGS, **(settings or {}))
    if I.get("wf_errors") and key != "wf_errors":
        st["errorWorkflow"] = I["wf_errors"]
    body = {"name": PREFIX + name, "nodes": nodes, "connections": conns, "settings": st}
    if key in I and api("GET", f"/workflows/{I[key]}", ok404=True):
        try:
            api("POST", f"/workflows/{I[key]}/deactivate")
        except SystemExit:
            pass
        api("PUT", f"/workflows/{I[key]}", body)
    else:
        I[key] = api("POST", "/workflows", body)["id"]
        save_ids(I)
    if activate:
        api("POST", f"/workflows/{I[key]}/activate")
    print("deployed", PREFIX + name, "(active)" if activate else "")


# =====================================================================================
# 08 Error alerts (built first so the others can point at it)
# =====================================================================================
def wf_errors():
    n = [node("Error Trigger", "n8n-nodes-base.errorTrigger", {}, (0, 0)),
         code("Write alert", js(r"""
const e = $input.first().json;
return [{ json: { lead_id: '', at: new Date().toISOString(), kind: 'error',
  title: `Workflow error: ${(e.workflow && e.workflow.name || '').replace('Front Desk | ', '')}`,
  detail: String((e.execution && e.execution.error && e.execution.error.message) || 'Unknown error').slice(0, 300),
  channel: 'system', sample: false } }];
"""), (240, 0)),
         dt_insert("Log alert", "activity", (480, 0)),
         note("## Error alerts\nAny Front Desk workflow that crashes lands here. The error is written to the activity log, "
              "so it shows on the console's Automations screen. In production this also sends a Telegram/Slack alert.", (0, -260), 520, 200)]
    c = {}
    chain(c, "Error Trigger", "Write alert", "Log alert")
    deploy("wf_errors", "08 Error Alerts", n, c)   # n8n 2.x: an error workflow must be published before others can select it


# =====================================================================================
# 10 Save lead (sub-workflow): upsert one lead row by lead_id, merging only the fields sent
# =====================================================================================
def wf_save_lead():
    n = [trigger_sub((0, 0)),
         dt_get("Find lead", "leads", (240, 0), "lead_id", "={{ $('Start').first().json.lead_id }}"),
         code("Merge", js(r"""
const COLS = __LEAD_COLS__;
const incoming = $('Start').first().json;
const found = $input.first().json || {};
const row = {};
for (const c of COLS) row[c] = (c in incoming) ? incoming[c] : (found[c] === undefined ? null : found[c]);
row.updated_at = new Date().toISOString();
if (!row.created_at) row.created_at = row.updated_at;
for (const c of ['score', 'crm_attempts']) row[c] = Number(row[c] || 0);
row.sample = !!row.sample;
for (const c of COLS) if (row[c] === null) row[c] = (c === 'score' || c === 'crm_attempts') ? 0 : (c === 'sample' ? false : '');
return [{ json: { exists: !!found.lead_id, ...row } }];
"""), (480, 0)),
         if_true("Exists?", "={{ $json.exists }}", (720, 0)),
         dt_update("Update lead", "leads", (960, -100), "lead_id", "={{ $json.lead_id }}", LEAD_COLS),
         code("Row only", js("const C = __LEAD_COLS__;\nreturn $input.all().map(i => ({ json: Object.fromEntries(C.map(c => [c, i.json[c]])) }));"), (960, 100)),
         dt_insert("Insert lead", "leads", (1200, 100))]
    c = {}
    chain(c, "Start", "Find lead", "Merge", "Exists?")
    link(c, "Exists?", "Update lead", 0)
    link(c, "Exists?", "Row only", 1)
    link(c, "Row only", "Insert lead")
    deploy("wf_save_lead", "10 Save Lead (sub)", n, c)


# =====================================================================================
# 11 CRM sync (sub-workflow): push one lead to the CRM, or report failure (caller queues it)
# =====================================================================================
def wf_crm_sync():
    n = [trigger_sub((0, 0)),
         dt_get("Outage switch", "settings", (240, 0), "key", "crm_outage"),
         code("Decide", js(r"""
const HUBSPOT = __HUBSPOT__;
const lead = $('Start').first().json;
const outage = String(($input.first().json || {}).value || 'off') === 'on';
if (outage) return [{ json: { ok: false, send: false, lead_id: lead.lead_id, crm: HUBSPOT ? 'HubSpot' : 'CRM', error: 'CRM API did not respond (simulated outage)' } }];
if (!HUBSPOT) return [{ json: { ok: true, send: false, lead_id: lead.lead_id, crm: 'Built-in CRM', crm_id: lead.crm_id || ('C-' + String(lead.lead_id).slice(2)) } }];
const parts = String(lead.name || '').trim().split(/\s+/);
const status = { New: 'NEW', Contacted: 'CONNECTED', Booked: 'OPEN_DEAL', Lost: 'UNQUALIFIED' }[lead.stage] || 'NEW';
const props = Object.fromEntries(Object.entries({
  firstname: parts[0] || '', lastname: parts.slice(1).join(' '), phone: lead.phone, email: lead.email,
  hs_lead_status: status, lifecyclestage: 'lead', message: [lead.service, lead.summary].filter(Boolean).join(' | ').slice(0, 1000),
}).filter(([, v]) => v));
let method = 'POST', url = 'https://api.hubapi.com/crm/v3/objects/contacts', body = { properties: props };
if (/^\d+$/.test(String(lead.crm_id || ''))) { method = 'PATCH'; url += '/' + lead.crm_id; delete props.lifecyclestage; }
else if (lead.email) { url += '/batch/upsert'; body = { inputs: [{ idProperty: 'email', id: lead.email, properties: props }] }; }
return [{ json: { send: true, method, url, body, lead_id: lead.lead_id } }];
"""), (480, 0)),
         note("## CRM sync\nOne standard lead shape in, one CRM out. Today: HubSpot (free CRM) when a token is set, "
              "otherwise the built-in CRM tables. Pipedrive and GoHighLevel are the same pattern: only the field map changes.\n"
              "**Outage switch** (console → Automations) makes this step fail on purpose so you can watch the retry queue keep the lead safe.",
              (0, -300), 700, 240)]
    c = {}
    chain(c, "Start", "Outage switch", "Decide")
    if HUBSPOT:
        hub = hubspot_cred()
        n += [if_true("Send to HubSpot?", "={{ $json.send }}", (720, 0)),
              node("HubSpot API", "n8n-nodes-base.httpRequest",
                   {"method": "={{ $json.method }}", "url": "={{ $json.url }}", "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth", "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {"timeout": 15000}},
                   (960, -100), tv=4.2, credentials={"httpHeaderAuth": hub}, onError="continueErrorOutput",
                   retryOnFail=True, maxTries=3, waitBetweenTries=1000),
              code("Synced", js(r"""
const r = $input.first().json;
const id = r.id || (r.results && r.results[0] && r.results[0].id) || '';
return [{ json: { ok: true, lead_id: $('Decide').first().json.lead_id, crm: 'HubSpot', crm_id: String(id) } }];
"""), (1200, -160)),
              code("Failed", js(r"""
const e = $input.first().json;
return [{ json: { ok: false, lead_id: $('Decide').first().json.lead_id, crm: 'HubSpot', error: String((e.error && (e.error.message || e.error)) || 'HubSpot error').slice(0, 200) } }];
"""), (1200, 40)),
              code("Pass", "return $input.all();", (960, 160))]
        link(c, "Decide", "Send to HubSpot?")
        link(c, "Send to HubSpot?", "HubSpot API", 0)
        link(c, "Send to HubSpot?", "Pass", 1)
        link(c, "HubSpot API", "Synced", 0)
        link(c, "HubSpot API", "Failed", 1)
    deploy("wf_crm_sync", "11 CRM Sync (sub)", n, c)


# =====================================================================================
# 01 Lead intake + AI qualification
# =====================================================================================
QUAL_SCHEMA = {"type": "object", "additionalProperties": False,
               "required": ["score", "temperature", "intent", "urgency", "summary", "next_action", "followup_message"],
               "properties": {
                   "score": {"type": "integer", "description": "0-100 likelihood to book soon"},
                   "temperature": {"type": "string", "enum": ["hot", "warm", "cold"]},
                   "intent": {"type": "string", "description": "What they want, max 8 words"},
                   "urgency": {"type": "string", "enum": ["emergency", "this_week", "flexible"]},
                   "summary": {"type": "string", "description": "One sentence for the front desk"},
                   "next_action": {"type": "string", "description": "Best next step, max 10 words"},
                   "followup_message": {"type": "string", "description": "WhatsApp follow-up to the patient, max 300 characters"}}}


def wf_lead():
    n = [webhook("demo-dental/lead", (0, 0)),
         code("Check form", js(r"""
const b = $input.first().json.body || {};
const s = v => String(v || '').trim().slice(0, 500);
const name = s(b.name), phone = s(b.phone).replace(/[^\d+]/g, ''), email = s(b.email).toLowerCase();
const err = !name ? 'Please add a name.' : phone.length < 7 ? 'Please add a valid phone number.' :
  (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) ? 'Please check the email address.' : '';
const now = new Date().toISOString();
const lead_id = 'L-' + Date.now().toString(36).toUpperCase().slice(-6);
return [{ json: { ok: !err, error: err, lead_id, created_at: now, updated_at: now, name, phone, email,
  service: s(b.service) || 'Check-up & cleaning', message: s(b.message), preferred_time: s(b.preferred_time),
  source: s(b.source) || 'Website form', stage: 'New', score: 0, temperature: '', intent: '', urgency: '',
  summary: '', next_action: 'AI qualifying…', followup: '', crm_status: 'pending', crm_id: '', crm_attempts: 0,
  crm_error: '', sample: false } }];
"""), (240, 0)),
         if_true("Form OK?", "={{ $json.ok }}", (480, 0)),
         respond("Reply: fix form", "={{ JSON.stringify({ ok: false, error: $json.error }) }}", (720, 200), 400),
         code("Lead row", js("const C = __LEAD_COLS__;\nconst j = $input.first().json;\nreturn [{ json: Object.fromEntries(C.map(c => [c, j[c]])) }];"), (720, -100)),
         run_sub("Save first", "wf_save_lead", (960, -100)),
         code("Received", js(r"""
const l = $('Lead row').first().json;
return [{ json: { lead_id: l.lead_id, at: new Date().toISOString(), kind: 'lead', title: 'New lead from the website form',
  detail: [l.service, l.message].filter(Boolean).join(' · ').slice(0, 300), channel: 'web', sample: false } }];
"""), (1200, -100)),
         dt_insert("Log received", "activity", (1440, -100)),
         respond("Reply: saved", "={{ JSON.stringify({ ok: true, lead_id: $('Lead row').first().json.lead_id }) }}", (1680, -100)),
         code("Build AI request", js(r"""
__CLINIC_JS__
const l = $('Lead row').first().json;
const schema = __SCHEMA__;
const today = nowLocal();
const body = {
  model: __MODEL__, store: false, reasoning: { effort: 'low' },
  text: { format: { type: 'json_schema', name: 'lead_qualification', strict: true, schema } },
  input: [
    { role: 'developer', content: `You qualify new patient leads for a dental clinic's front desk. Today is ${fmtDay(today)}.
Score 0-100 how likely this person books soon. Raise the score for: pain or urgency, a clear time wish, high-value care
(implants, aligners, crowns, root canal), a complete contact (phone and email), insurance or budget mentioned.
Lower it for vague or price-only questions. hot >= 70, warm 40-69, cold < 40.
The follow-up message is a short, warm WhatsApp text from the clinic: use the first name, mention what they asked
about, offer to book, sign as "${CLINIC.assistant}, ${CLINIC.name}". Use only facts from the fact sheet; never invent prices,
discounts or medical advice. If there is pain, add that same-day emergency slots exist.
Fact sheet:
${factSheet()}` },
    { role: 'user', content: JSON.stringify({ name: l.name, service: l.service, message: l.message, preferred_time: l.preferred_time, has_email: !!l.email, has_phone: !!l.phone }) },
  ],
};
return [{ json: { body } }];
""").replace("__SCHEMA__", json.dumps(QUAL_SCHEMA)), (1920, -100)),
         openai("Ask OpenAI", (2160, -100)),
         code("Read AI result", js(r"""
__CLINIC_JS__
const q = JSON.parse(outText($input.first().json));
return [{ json: { q, by: 'AI' } }];
"""), (2400, -200), onError="continueErrorOutput"),
         code("Rule-based fallback", js(r"""
// OpenAI failed: score with simple rules so the lead still moves (never stuck, never lost).
const l = $('Lead row').first().json;
const t = (l.service + ' ' + l.message).toLowerCase();
let score = 40;
if (/pain|hurt|broken|swell|emergency|bleed/.test(t)) score += 35;
if (/implant|aligner|crown|root canal/.test(t)) score += 20;
if (l.email) score += 5;
const temperature = score >= 70 ? 'hot' : score >= 40 ? 'warm' : 'cold';
const first = l.name.split(' ')[0];
return [{ json: { by: 'Rules (AI unavailable)', q: { score: Math.min(score, 95), temperature, intent: l.service, urgency: score >= 75 ? 'this_week' : 'flexible',
  summary: `${l.name} asked about ${l.service}.`, next_action: 'Call back and offer two times',
  followup_message: `Hi ${first}, thanks for contacting us about ${l.service}. Would you like us to book a time for you? Reply with a day that suits you.` } } }];
"""), (2400, 0)),
         code("Lead for CRM", js(r"""
const l = $('Lead row').first().json;
const { q, by } = $input.first().json;
return [{ json: { ...l, qualified_by: by, score: q.score, temperature: q.temperature, intent: q.intent, urgency: q.urgency, summary: q.summary,
  next_action: q.next_action, followup: q.followup_message } }];
"""), (2640, -100)),
         run_sub("CRM sync", "wf_crm_sync", (2880, -100)),
         code("Final lead", js(r"""
const l = $('Lead for CRM').first().json;
const r = $input.first().json;
const by = l.qualified_by || 'AI';
const out = { ...l, crm_status: r.ok ? 'synced' : 'queued', crm_id: r.crm_id || '', crm_attempts: 1, crm_error: r.ok ? '' : (r.error || '') };
const now = Date.now();
const at = k => new Date(now + k).toISOString();
const acts = [
  { kind: 'ai', title: `AI qualified the lead: ${l.temperature} · ${l.score}/100`, detail: `${l.intent}. Urgency: ${String(l.urgency).replace('_', ' ')}. Next: ${l.next_action}. (${by})` },
  r.ok ? { kind: 'crm', title: `Saved to ${r.crm}`, detail: r.crm_id ? `Record ${r.crm_id}` : '' }
       : { kind: 'queue', title: 'CRM not responding: lead kept safe in the retry queue', detail: `${r.error}. Retrying every 2 minutes.` },
  { kind: 'followup', title: 'WhatsApp follow-up written and queued', detail: l.followup },
].map((a, i) => ({ lead_id: l.lead_id, at: at(i + 1), channel: a.kind === 'followup' ? 'whatsapp' : 'system', sample: false, ...a }));
return [{ json: { lead: out, acts } }];
"""), (3120, -100)),
         code("Lead fields", "return [{ json: $input.first().json.lead }];", (3360, -100)),
         run_sub("Save lead", "wf_save_lead", (3600, -100)),
         code("Activity rows", "return $('Final lead').first().json.acts.map(a => ({ json: a }));", (3840, -100)),
         dt_insert("Log activity", "activity", (4080, -100)),
         note("## 01 · Lead intake\n**Save first:** the lead is written to the database before any other API is called, "
              "so it can never be lost. Then the website gets its reply (fast), and the rest runs in the background.", (0, -420), 1000, 220),
         note("## AI qualification\nOpenAI scores the lead (0-100, hot/warm/cold), names the intent and urgency, and writes the WhatsApp follow-up.\n"
              "**If OpenAI fails:** a rule-based score takes over, so the lead still moves.", (1900, -420), 760, 220),
         note("## CRM + log\nCRM sync (sub-workflow) → if it fails, the lead is marked **queued** and workflow 06 retries it every 2 minutes.\n"
              "Every step writes to the activity log the console shows.", (2860, -420), 1300, 220)]
    c = {}
    chain(c, "Webhook", "Check form", "Form OK?")
    link(c, "Form OK?", "Lead row", 0)
    link(c, "Form OK?", "Reply: fix form", 1)
    chain(c, "Lead row", "Save first", "Received", "Log received", "Reply: saved", "Build AI request", "Ask OpenAI")
    link(c, "Ask OpenAI", "Read AI result", 0)
    link(c, "Ask OpenAI", "Rule-based fallback", 1)
    link(c, "Read AI result", "Lead for CRM", 0)
    link(c, "Read AI result", "Rule-based fallback", 1)
    link(c, "Rule-based fallback", "Lead for CRM")
    chain(c, "Lead for CRM", "CRM sync", "Final lead", "Lead fields", "Save lead", "Activity rows", "Log activity")
    deploy("wf_lead", "01 Lead Intake + AI Qualification", n, c)


# =====================================================================================
# 02 Voice agent tools (ElevenLabs server tools call this)
# =====================================================================================
RUN_TOOL_JS = r"""
__CLINIC_JS__
const req = $('Webhook').first().json;
const tool = __TOOL_EXPR__;
const a = __ARGS_EXPR__;
const appts = $('Get appointments').all().map(i => i.json).filter(x => x.appt_id);
const leads = $('Get leads').all().map(i => i.json).filter(x => x.lead_id);
const taken = takenSet(appts);
const leadId = String(a.lead_id || '').trim() || newId('L');
const lead = leads.find(l => l.lead_id === leadId) || null;
const channel = a.channel === 'chat' ? 'chat' : 'voice';
const nowIso = new Date().toISOString();
let response = {}, appt = null, cancelId = null, patch = null;
const acts = [];
const act = (kind, title, detail) => acts.push({ lead_id: leadId, at: new Date(Date.now() + acts.length).toISOString(), kind, title, detail: detail || '', channel, sample: false });
const newLeadBase = () => lead ? {} : { source: channel === 'chat' ? 'WhatsApp chat (AI)' : 'Phone call (AI)', stage: 'New', crm_status: 'pending' };

if (tool === 'check_availability') {
  const r = daySlots(a.date, taken);
  if (r.error) response = { ok: false, message: 'I could not read that date. Ask the caller for the date again.' };
  else {
    const times = pick(r.slots, a.time_of_day || 'any').map(fmtTime);
    response = times.length
      ? { ok: true, date: r.day.toISODate(), day: fmtDay(r.day), free_times: times, rule: 'Offer two or three of these times only.' }
      : { ok: true, date: r.day.toISODate(), day: fmtDay(r.day), free_times: [], reason: r.closed ? 'The clinic is closed that day.' : 'No free times left that day.', next_open_days: nextOpen(r.day, taken, 2) };
    act('tool', 'AI checked free times', `${fmtDay(r.day)}: ${times.length ? times.join(', ') : (r.closed ? 'closed' : 'fully booked')}`);
  }
} else if (tool === 'book_appointment') {
  const t = parseTime(a.time), r = daySlots(a.date, taken);
  const name = String(a.name || (lead && lead.name) || '').trim(), phone = String(a.phone || (lead && lead.phone) || '').trim();
  if (!t || r.error) response = { ok: false, booked: false, message: 'Date or time not understood. Confirm them again.' };
  else if (!name) response = { ok: false, booked: false, message: "Ask for the patient's full name first." };
  else {
    const want = r.day.set({ hour: t.h, minute: t.mi });
    const free = r.slots.find(s => s.toMillis() === want.toMillis());
    if (!free) {
      response = { ok: true, booked: false, message: 'That time is not available.', other_free_times_that_day: pick(r.slots, 'any').map(fmtTime), next_open_days: r.slots.length ? [] : nextOpen(r.day, taken, 2) };
      act('tool', 'Requested time is taken: AI offered other times', `${fmtDay(want)} ${fmtTime(want)}`);
    } else {
      const id = newId('A'), service = String(a.service || (lead && lead.service) || 'Check-up & cleaning');
      appt = { appt_id: id, lead_id: leadId, name, phone, service, start: want.toISO(), status: 'booked', source: channel === 'chat' ? 'AI chat' : 'AI call', created_at: nowIso, sample: false };
      response = { ok: true, booked: true, appointment_id: id, when: `${fmtDay(want)} at ${fmtTime(want)}`, service, next: 'Read the day, time and service back to the patient, then ask if there is anything else.' };
      patch = clean({ lead_id: leadId, ...newLeadBase(), name, phone, service, stage: 'Booked', next_action: `Visit: ${fmtDay(want)}, ${fmtTime(want)}` });
      act('appointment', `Appointment booked by AI (${channel === 'chat' ? 'chat' : 'call'})`, `${service} · ${fmtDay(want)} at ${fmtTime(want)}`);
    }
  }
} else if (tool === 'find_booking') {
  const phone = String(a.phone || '').replace(/[^\d]/g, '');
  const mine = appts.filter(x => x.status === 'booked' && (x.lead_id === leadId || (phone && String(x.phone).replace(/[^\d]/g, '').endsWith(phone.slice(-7)))))
    .filter(x => DateTime.fromISO(x.start) > DateTime.now());
  response = { ok: true, upcoming: mine.map(x => { const d = DateTime.fromISO(x.start, { setZone: true }).setZone(TZ); return { appointment_id: x.appt_id, service: x.service, when: `${fmtDay(d)} at ${fmtTime(d)}` }; }) };
  act('tool', 'AI looked up bookings', mine.length ? `${mine.length} upcoming` : 'none found');
} else if (tool === 'cancel_appointment') {
  const x = appts.find(y => y.appt_id === String(a.appointment_id || '').trim() && y.status === 'booked');
  if (!x) response = { ok: false, message: 'No active booking with that id. Use find_booking first.' };
  else {
    cancelId = x.appt_id;
    response = { ok: true, cancelled: true, message: 'Cancelled. Offer to book a new time.' };
    patch = { lead_id: leadId, stage: 'Contacted', next_action: 'Rebook: cancelled by patient' };
    act('appointment', 'Appointment cancelled by AI', `${x.service} · ${x.start.slice(0, 16).replace('T', ' ')}`);
  }
} else if (tool === 'save_caller_details') {
  patch = clean({ lead_id: leadId, ...newLeadBase(), name: a.name, phone: a.phone, email: a.email, service: a.service,
    message: a.notes, urgency: a.urgency });
  response = { ok: true, saved: true };
  act('crm', 'AI saved caller details to the CRM', [a.name, a.service, a.urgency].filter(Boolean).join(' · '));
} else if (tool === 'request_callback') {
  patch = clean({ lead_id: leadId, ...newLeadBase(), next_action: `Staff callback: ${String(a.reason || '').slice(0, 80)}`, urgency: a.urgency });
  response = { ok: true, task_created: true, message: 'A team member will call back. Tell the caller when: within 30 minutes during opening hours.' };
  act('task', `Callback task for the front desk${a.urgency === 'emergency' ? ' (urgent)' : ''}`, String(a.reason || ''));
} else {
  response = { ok: false, message: 'Unknown tool' };
}
return [{ json: { response, appt, cancelId, patch, acts } }];
"""


def tool_writes(n, c, src, x0, y0):
    """Branches after the decision node: write appointment, cancel, lead, activity; reply last (lowest)."""
    n += [code("Appointment row", f"const a = $('{src}').first().json.appt;\nreturn a ? [{{ json: a }}] : [];", (x0, y0 - 300)),
          dt_insert("Insert appointment", "appointments", (x0 + 240, y0 - 300)),
          code("Cancel row", f"const id = $('{src}').first().json.cancelId;\nreturn id ? [{{ json: {{ appt_id: id, status: 'cancelled' }} }}] : [];", (x0, y0 - 150)),
          dt_update("Cancel appointment", "appointments", (x0 + 240, y0 - 150), "appt_id", "={{ $json.appt_id }}", ["status"]),
          code("Lead patch", f"const p = $('{src}').first().json.patch;\nreturn p ? [{{ json: p }}] : [];", (x0, y0)),
          run_sub("Save lead", "wf_save_lead", (x0 + 240, y0)),
          code("Activity rows", f"return ($('{src}').first().json.acts || []).map(a => ({{ json: a }}));", (x0, y0 + 150)),
          dt_insert("Log activity", "activity", (x0 + 240, y0 + 150))]
    for a, b in [("Appointment row", "Insert appointment"), ("Cancel row", "Cancel appointment"),
                 ("Lead patch", "Save lead"), ("Activity rows", "Log activity")]:
        link(c, src, a)
        link(c, a, b)


def wf_tools():
    n = [webhook("demo-dental/tool", (0, 0)),
         dt_get("Get appointments", "appointments", (240, 0)),
         dt_get("Get leads", "leads", (480, 0)),
         code("Run tool", js(RUN_TOOL_JS.replace("__TOOL_EXPR__", "String((req.query && req.query.name) || (req.body && req.body.tool) || '')")
                             .replace("__ARGS_EXPR__", "req.body || {}")), (720, 0)),
         respond("Reply to agent", "={{ JSON.stringify($('Run tool').first().json.response) }}", (960, 400)),
         note("## 02 · Voice agent tools (function calling)\nThe ElevenLabs voice agent calls `/tool?name=<tool>` while it talks:\n"
              "`check_availability` · `book_appointment` · `find_booking` · `cancel_appointment` · `save_caller_details` · `request_callback`.\n"
              "**Anti-hallucination:** the AI never guesses a time. Free slots come only from the real bookings table; "
              "a taken slot is refused and alternatives are offered.", (0, -560), 760, 260)]
    c = {}
    chain(c, "Webhook", "Get appointments", "Get leads", "Run tool")
    tool_writes(n, c, "Run tool", 960, 0)
    link(c, "Run tool", "Reply to agent")
    deploy("wf_tools", "02 Voice Agent Tools", n, c)


# =====================================================================================
# 03 After-call processing
# =====================================================================================
CALL_SCHEMA = {"type": "object", "additionalProperties": False,
               "required": ["outcome", "sentiment", "summary", "next_action", "followup_message", "lead_score", "intent", "urgency"],
               "properties": {
                   "lead_score": {"type": "integer", "description": "0-100 likelihood this caller becomes a patient soon"},
                   "intent": {"type": "string", "description": "What the caller wants, max 8 words"},
                   "urgency": {"type": "string", "enum": ["emergency", "this_week", "flexible"]},
                   "outcome": {"type": "string", "enum": ["booked", "callback_requested", "question_answered", "not_interested", "no_conversation"]},
                   "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                   "summary": {"type": "string", "description": "Two short sentences for the CRM note"},
                   "next_action": {"type": "string", "description": "Max 10 words"},
                   "followup_message": {"type": "string", "description": "WhatsApp text after the call, max 300 characters; empty if booked or no conversation"}}}


def wf_after_call():
    n = [webhook("demo-dental/call-ended", (0, 0)),
         dt_get("Get lead", "leads", (240, 0), "lead_id", "={{ $('Webhook').first().json.body.lead_id }}"),
         dt_get("Get appointments", "appointments", (480, 0), "lead_id", "={{ $('Webhook').first().json.body.lead_id }}"),
         code("Build AI request", js(r"""
__CLINIC_JS__
const b = $('Webhook').first().json.body || {};
const lines = (b.transcript || []).map(t => `${t.role === 'agent' ? 'AI' : 'Caller'}: ${t.message}`).join('\n').slice(0, 12000);
const schema = __SCHEMA__;
return [{ json: { lines, body: { model: __MODEL__, store: false, reasoning: { effort: 'low' },
  text: { format: { type: 'json_schema', name: 'call_summary', strict: true, schema } },
  input: [
    { role: 'developer', content: `Summarise a phone call between ${CLINIC.name}'s AI receptionist and a caller, for the CRM.
Outcome "booked" only if the transcript shows a confirmed booking. Be factual: no details that are not in the transcript.
The follow-up message is a warm WhatsApp text from the clinic, signed "${CLINIC.assistant}, ${CLINIC.name}"; leave it empty if the call booked a visit or there was no real conversation.` },
    { role: 'user', content: lines || '(no speech)' },
  ] } } }];
""").replace("__SCHEMA__", json.dumps(CALL_SCHEMA)), (720, 0)),
         openai("Ask OpenAI", (960, 0)),
         code("Apply", js(r"""
__CLINIC_JS__
const b = $('Webhook').first().json.body || {};
let s;
try { s = JSON.parse(outText($('Ask OpenAI').first().json)); } catch (e) { s = null; }
if (!s || $input.first().json.error) s = { outcome: 'question_answered', sentiment: 'neutral', summary: 'Call ended. AI summary unavailable; transcript saved.', next_action: 'Review the transcript', followup_message: '', lead_score: 50, intent: '', urgency: 'flexible' };
const lead = $('Get lead').first().json || {};
const startedAt = b.started_at || new Date(Date.now() - (b.duration_secs || 0) * 1000).toISOString();
const bookedNow = $('Get appointments').all().map(i => i.json).filter(a => a.appt_id && a.status === 'booked' && a.created_at >= startedAt);
const outcome = bookedNow.length ? 'booked' : (s.outcome === 'booked' ? 'question_answered' : s.outcome);
const secs = Math.round(Number(b.duration_secs || 0));
const mmss = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
const label = { booked: 'Booked', callback_requested: 'Callback requested', question_answered: 'Question answered', not_interested: 'Not interested', no_conversation: 'No conversation' }[outcome];
const call = { call_id: String(b.conversation_id || newId('C')), lead_id: String(b.lead_id || ''), name: lead.name || 'Unknown caller',
  direction: b.direction === 'outbound' ? 'outbound' : 'inbound', started_at: startedAt, duration_secs: secs, outcome: label,
  sentiment: s.sentiment, summary: s.summary, transcript: JSON.stringify((b.transcript || []).slice(0, 80)).slice(0, 20000),
  tools_used: (b.tools || []).join(', '), sample: false };
const stage = outcome === 'booked' ? 'Booked' : outcome === 'not_interested' ? 'Lost' : (lead.stage === 'Booked' ? 'Booked' : 'Contacted');
const score = Math.max(0, Math.min(100, Math.round(Number(s.lead_score || 0)) + (bookedNow.length ? 10 : 0)));
const scored = lead.temperature ? {} : { score: Math.min(score, 100), temperature: score >= 70 ? 'hot' : score >= 40 ? 'warm' : 'cold', intent: s.intent || '', urgency: s.urgency || '' };
const patch = lead.lead_id ? { lead_id: lead.lead_id, stage, next_action: s.next_action, summary: s.summary, ...scored } : null;
const at = k => new Date(Date.now() + k).toISOString();
const acts = [{ lead_id: call.lead_id, at: at(0), kind: 'call', title: `AI ${call.direction} call · ${mmss} · ${label}`, detail: s.summary, channel: 'voice', sample: false }];
if (s.followup_message && outcome !== 'booked' && outcome !== 'no_conversation')
  acts.push({ lead_id: call.lead_id, at: at(1), kind: 'followup', title: 'WhatsApp follow-up written after the call', detail: s.followup_message, channel: 'whatsapp', sample: false });
return [{ json: { call, patch, acts, reply: { ok: true, outcome: label, sentiment: s.sentiment, summary: s.summary, next_action: s.next_action, followup: s.followup_message, booked: bookedNow.length > 0 } } }];
"""), (1200, 0)),
         code("Call row", "return [{ json: $input.first().json.call }];", (1440, -200)),
         dt_insert("Save call", "calls", (1680, -200)),
         code("Lead patch", "const p = $('Apply').first().json.patch;\nreturn p ? [{ json: p }] : [];", (1440, 0)),
         run_sub("Save lead", "wf_save_lead", (1680, 0)),
         run_sub("CRM sync", "wf_crm_sync", (1920, 0)),
         code("CRM result", js(r"""
const r = $input.first().json, p = $('Apply').first().json.patch;
return [{ json: { lead_id: p.lead_id, crm_status: r.ok ? 'synced' : 'queued', crm_error: r.ok ? '' : (r.error || ''), ...(r.crm_id ? { crm_id: r.crm_id } : {}) } }];
"""), (2160, 0)),
         run_sub("Save CRM status", "wf_save_lead", (2400, 0)),
         code("Activity rows", "return $('Apply').first().json.acts.map(a => ({ json: a }));", (1440, 200)),
         dt_insert("Log activity", "activity", (1680, 200)),
         respond("Reply", "={{ JSON.stringify($('Apply').first().json.reply) }}", (1440, 400)),
         note("## 03 · After the call\nTranscript → OpenAI writes the CRM note (outcome, sentiment, summary, next step, follow-up). "
              "The outcome is cross-checked with the bookings table, so a \"booked\" call really has a booking. "
              "Then: call log, lead stage, CRM sync, activity log.", (0, -360), 960, 220)]
    c = {}
    chain(c, "Webhook", "Get lead", "Get appointments", "Build AI request", "Ask OpenAI")
    link(c, "Ask OpenAI", "Apply", 0)
    link(c, "Ask OpenAI", "Apply", 1)
    for a, b in [("Apply", "Call row"), ("Call row", "Save call"), ("Apply", "Lead patch"), ("Lead patch", "Save lead"),
                 ("Save lead", "CRM sync"), ("CRM sync", "CRM result"), ("CRM result", "Save CRM status"),
                 ("Apply", "Activity rows"), ("Activity rows", "Log activity"), ("Apply", "Reply")]:
        link(c, a, b)
    deploy("wf_after_call", "03 After-Call Processing", n, c)


# =====================================================================================
# 04 Patient chat agent (WhatsApp-ready): starts as a copy of the Answer Engine, then customised
# =====================================================================================
CHAT_SCHEMA = {"type": "object", "additionalProperties": False,
               "required": ["reply", "action", "date", "time", "time_of_day", "service", "name", "phone"],
               "properties": {
                   "reply": {"type": "string", "description": "Message to the patient (used when action is none or human)"},
                   "action": {"type": "string", "enum": ["none", "check_availability", "book_appointment", "request_callback"]},
                   "date": {"type": "string", "description": "YYYY-MM-DD or empty"},
                   "time": {"type": "string", "description": "HH:MM 24h or empty"},
                   "time_of_day": {"type": "string", "enum": ["any", "morning", "afternoon"]},
                   "service": {"type": "string"}, "name": {"type": "string"}, "phone": {"type": "string"}}}


def copy_answer_engine():
    """Step 1 (once): a complete, untouched copy of the Answer Engine under a new name and webhook path."""
    if I.get("wf_chat") and api("GET", f"/workflows/{I['wf_chat']}", ok404=True):
        return
    orig = json.loads((CFG / "original_answer_engine_backup.json").read_text())
    nodes = json.loads(json.dumps(orig["nodes"]))
    for nd in nodes:
        nd["id"] = str(uuid.uuid4())
        if nd["type"] == "n8n-nodes-base.webhook":
            nd["parameters"]["path"] = "demo-dental/chat"
            nd["webhookId"] = str(uuid.uuid4())
            nd["credentials"] = {"httpHeaderAuth": webhook_cred()}
    st = {k: v for k, v in orig.get("settings", {}).items() if k in SETTINGS or k in ("binaryMode",)}
    I["wf_chat"] = api("POST", "/workflows", {"name": PREFIX + "04 Patient Chat Agent", "nodes": nodes,
                                              "connections": orig["connections"], "settings": st})["id"]
    save_ids(I)
    print("copied Answer Engine -> Front Desk | 04 Patient Chat Agent (inactive copy)")


def wf_chat():
    copy_answer_engine()
    n = [webhook("demo-dental/chat", (0, 0)),
         code("Check input", js(r"""
const b = $input.first().json.body || {};
const message = String(b.message || '').trim().slice(0, 600);
const history = (Array.isArray(b.history) ? b.history : []).slice(-12).map(h => ({ role: h.role === 'assistant' ? 'assistant' : 'user', content: String(h.content || '').slice(0, 600) }));
return [{ json: { ok: message.length > 0, message, history, lead_id: String(b.lead_id || '').slice(0, 40), error: 'Empty message' } }];
"""), (240, 0)),
         if_true("Input OK?", "={{ $json.ok }}", (480, 0)),
         respond("Reply: bad input", "={{ JSON.stringify({ ok: false, error: 'bad_input' }) }}", (720, 200), 400),
         dt_get("Get appointments", "appointments", (720, -100)),
         dt_get("Get leads", "leads", (960, -100)),
         code("Build request", js(r"""
__CLINIC_JS__
const inp = $('Check input').first().json;
const schema = __SCHEMA__;
const today = nowLocal();
const days = [...Array(14).keys()].map(i => today.plus({ days: i })).map(d => `${d.toFormat('ccc d LLL')} = ${d.toISODate()}`).join(', ');
const body = { model: __MODEL__, store: false, reasoning: { effort: 'low' },
  text: { format: { type: 'json_schema', name: 'chat_turn', strict: true, schema } },
  input: [
    { role: 'developer', content: `You are ${CLINIC.assistant}, the WhatsApp assistant of ${CLINIC.name}. Reply in the patient's language, short and warm (max 3 sentences), one question at a time.
Answer ONLY from the fact sheet. If something is not in it, say the team will confirm and set action "request_callback". Never give a diagnosis or medical advice.
Booking: to show free times set action "check_availability" with date (and time_of_day). To book set action "book_appointment" only when you have date, time, service and the patient's full name; ask for anything missing first. Never state a free time yourself: the system finds real ones.
Now: ${today.toFormat("cccc d LLLL yyyy, HH:mm")}. Calendar: ${days}.
Fact sheet:
${factSheet()}` },
    ...inp.history,
    { role: 'user', content: inp.message },
  ] };
return [{ json: { body } }];
""").replace("__SCHEMA__", json.dumps(CHAT_SCHEMA)), (1200, -100)),
         openai("Ask OpenAI", (1440, -100)),
         code("Run action", js(CHAT_ACTION_JS), (1680, -100)),
         note("## 04 · Patient chat agent (WhatsApp-ready)\nStarted as a full copy of an existing answer-engine workflow, then customised. "
              "One OpenAI call returns the reply **and** an action. Times and bookings are done by code against the real bookings table, "
              "so the AI never invents a free slot. In production the Webhook is swapped for the WhatsApp Cloud API trigger; the rest stays.", (0, -440), 1200, 240)]
    c = {}
    chain(c, "Webhook", "Check input", "Input OK?")
    link(c, "Input OK?", "Get appointments", 0)
    link(c, "Input OK?", "Reply: bad input", 1)
    chain(c, "Get appointments", "Get leads", "Build request", "Ask OpenAI")
    link(c, "Ask OpenAI", "Run action", 0)
    link(c, "Ask OpenAI", "Run action", 1)
    tool_writes(n, c, "Run action", 1920, -100)
    n.append(respond("Reply", "={{ JSON.stringify($('Run action').first().json.reply) }}", (1920, 300)))
    link(c, "Run action", "Reply")
    deploy("wf_chat", "04 Patient Chat Agent", n, c)


CHAT_ACTION_JS = r"""
__CLINIC_JS__
const inp = $('Check input').first().json;
let ai = null;
try { ai = JSON.parse(outText($('Ask OpenAI').first().json)); } catch (e) { ai = null; }
if (!ai) return [{ json: { reply: { ok: false, reply: 'Sorry, I could not answer just now. Please try again in a moment.' }, appt: null, cancelId: null, patch: null, acts: [] } }];
const runTool = (tool, a) => {
""" + RUN_TOOL_JS.replace("__CLINIC_JS__", "").replace("const req = $('Webhook').first().json;\n", "") \
    .replace("const tool = __TOOL_EXPR__;\n", "").replace("const a = __ARGS_EXPR__;\n", "") \
    .replace("return [{ json: { response, appt, cancelId, patch, acts } }];", "return { response, appt, cancelId, patch, acts };") + r"""
};
const args = { lead_id: inp.lead_id, channel: 'chat', date: ai.date, time: ai.time, time_of_day: ai.time_of_day, service: ai.service, name: ai.name, phone: ai.phone, reason: ai.reply, urgency: '' };
let out = { response: null, appt: null, cancelId: null, patch: null, acts: [] };
let text = ai.reply;
if (ai.action === 'check_availability') {
  out = runTool('check_availability', args);
  const r = out.response;
  if (!r.ok) text = 'Which day would suit you? You can say a date like "tomorrow" or "Thursday".';
  else if (r.free_times.length) text = `Free times on ${r.day}: ${r.free_times.join(', ')}. Which one should I book for you?`;
  else text = `${r.reason} ` + (r.next_open_days.length ? 'Next free times: ' + r.next_open_days.map(d => `${d.day} (${d.times.join(', ')})`).join('; ') + '. Would one of these work?' : 'Could another day work?');
} else if (ai.action === 'book_appointment') {
  out = runTool('book_appointment', args);
  const r = out.response;
  if (r.booked) text = `Done! You're booked for ${r.service} on ${r.when}. Please arrive 10 minutes early and bring a photo ID. See you then!`;
  else if (r.ok) text = `Sorry, that time was just taken. ${(r.other_free_times_that_day || []).length ? 'Free that day: ' + r.other_free_times_that_day.join(', ') + '.' : 'That day is full.'} Which would you like?`;
  else text = r.message.includes('name') ? 'Could I have your full name for the booking?' : 'Could you confirm the day and time once more?';
} else if (ai.action === 'request_callback') {
  out = runTool('request_callback', args);
}
const leadId = (out.patch && out.patch.lead_id) || inp.lead_id || '';
const acts = [{ lead_id: leadId, at: new Date(Date.now() - 5).toISOString(), kind: 'chat', title: 'Patient message on WhatsApp chat', detail: inp.message.slice(0, 200), channel: 'whatsapp', sample: false },
  ...out.acts.map(x => ({ ...x, lead_id: x.lead_id || leadId })),
  { lead_id: leadId, at: new Date(Date.now() + 50).toISOString(), kind: 'chat', title: 'AI replied on WhatsApp chat', detail: text.slice(0, 200), channel: 'whatsapp', sample: false }];
return [{ json: { reply: { ok: true, reply: text, action: ai.action, booked: !!(out.response && out.response.booked), lead_id: leadId }, appt: out.appt, cancelId: out.cancelId, patch: out.patch, acts } }];
"""


# =====================================================================================
# 05 Comment filter
# =====================================================================================
COMMENT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["results"],
                  "properties": {"results": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False,
                      "required": ["index", "label", "reply_needed", "reply", "reason"],
                      "properties": {"index": {"type": "integer"},
                                     "label": {"type": "string", "enum": ["enquiry", "booking_request", "complaint", "praise", "spam", "off_topic"]},
                                     "reply_needed": {"type": "boolean"},
                                     "reply": {"type": "string", "description": "Public reply, max 220 characters; empty if no reply"},
                                     "reason": {"type": "string", "description": "Why, max 12 words"}}}}}}


def wf_comments():
    n = [webhook("demo-dental/comments", (0, 0)),
         code("Build request", js(r"""
__CLINIC_JS__
const b = $input.first().json.body || {};
const list = (Array.isArray(b.comments) ? b.comments : []).slice(0, 12).map((c, i) => ({ index: i, author: String(c.author || '').slice(0, 40), text: String(c.text || '').slice(0, 400) }));
const schema = __SCHEMA__;
return [{ json: { list, body: { model: __MODEL__, store: false, reasoning: { effort: 'low' },
  text: { format: { type: 'json_schema', name: 'comment_filter', strict: true, schema } },
  input: [
    { role: 'developer', content: `You moderate Facebook and Instagram comments for ${CLINIC.name}.
Label each comment. Reply ONLY to enquiry and booking_request (and politely to a complaint: apologise and invite them to message privately; never argue in public).
Do not reply to praise (a like is enough), spam or off_topic. Replies are short, friendly, use facts from the fact sheet only, and for bookings invite them to WhatsApp/DM.
Never share personal or medical details in public.
Fact sheet:
${factSheet()}` },
    { role: 'user', content: JSON.stringify(list) },
  ] } } }];
""").replace("__SCHEMA__", json.dumps(COMMENT_SCHEMA)), (240, 0)),
         openai("Ask OpenAI", (480, 0)),
         code("Read result", js(r"""
__CLINIC_JS__
let r = null;
try { r = JSON.parse(outText($input.first().json)); } catch (e) {}
return [{ json: r ? { ok: true, results: r.results } : { ok: false, error: 'AI busy, please retry' } }];
"""), (720, 0)),
         respond("Reply", "={{ JSON.stringify($json) }}", (960, 0)),
         note("## 05 · Comment filter\nLabels each comment (enquiry, booking request, complaint, praise, spam, off-topic) and drafts a public reply "
              "only where one is useful. In production the input is the Facebook/Instagram Graph API webhook.", (0, -300), 760, 200)]
    c = {}
    chain(c, "Webhook", "Build request", "Ask OpenAI")
    link(c, "Ask OpenAI", "Read result", 0)
    link(c, "Ask OpenAI", "Read result", 1)
    chain(c, "Read result", "Reply")
    deploy("wf_comments", "05 Comment Filter", n, c, settings={"saveDataSuccessExecution": "none"})


# =====================================================================================
# 06 CRM retry queue (every 2 minutes)
# =====================================================================================
def wf_retry():
    n = [node("Every 2 minutes", "n8n-nodes-base.scheduleTrigger",
              {"rule": {"interval": [{"field": "minutes", "minutesInterval": 2}]}}, (0, 0), tv=1.2),
         dt_get("Outage switch", "settings", (240, 0), "key", "crm_outage"),
         dt_get("Queued leads", "leads", (480, 0)),
         code("Pick", js(r"""
if (String($('Outage switch').first().json.value || 'off') === 'on') return [];
const stale = l => l.crm_status === 'pending' && Date.now() - new Date(l.created_at).getTime() > 3 * 60 * 1000;
return $input.all().map(i => i.json).filter(l => l.lead_id && (l.crm_status === 'queued' || stale(l))).slice(0, 10).map(l => ({ json: l }));
"""), (720, 0)),
         run_sub("CRM sync", "wf_crm_sync", (960, 0), each=True),
         code("Results", js(r"""
const leads = $('Pick').all().map(i => i.json);
const res = $input.all().map(i => i.json);
const out = [];
res.forEach((r, k) => {
  const l = leads.find(x => x.lead_id === r.lead_id) || leads[k];
  if (!l) return;
  const attempts = Number(l.crm_attempts || 0) + 1;
  out.push({ json: { patch: { lead_id: l.lead_id, crm_status: r.ok ? 'synced' : 'queued', crm_attempts: attempts, crm_error: r.ok ? '' : (r.error || ''), ...(r.crm_id ? { crm_id: r.crm_id } : {}) },
    act: { lead_id: l.lead_id, at: new Date().toISOString(), kind: r.ok ? 'crm' : 'queue', channel: 'system', sample: false,
      title: r.ok ? `Retry worked: synced to ${r.crm} (attempt ${attempts})` : `Retry ${attempts} failed: still safe in the queue`, detail: r.ok ? (r.crm_id ? `Record ${r.crm_id}` : '') : (r.error || '') } } });
});
return out;
"""), (1200, 0)),
         code("Patches", "return $input.all().map(i => ({ json: i.json.patch }));", (1440, -100)),
         run_sub("Save lead", "wf_save_lead", (1680, -100), each=True),
         code("Activity rows", "return $('Results').all().map(i => ({ json: i.json.act }));", (1440, 100)),
         dt_insert("Log activity", "activity", (1680, 100)),
         code("Outage too old?", js(r"""
// Demo safety: a simulated outage switches itself off after 10 minutes, so the next visitor finds a working CRM.
const s = $input.first().json || {};
const on = String(s.value || 'off') === 'on';
const since = new Date(s.updatedAt || s.createdAt || Date.now()).getTime();
return on && Date.now() - since > 10 * 60 * 1000 ? [{ json: { key: 'crm_outage', value: 'off' } }] : [];
"""), (480, -220)),
         dt_update("Switch off", "settings", (720, -220), "key", "crm_outage", ["value"]),
         code("Auto-off log", "return [{ json: { lead_id: '', at: new Date().toISOString(), kind: 'crm', title: 'Simulated outage ended automatically after 10 minutes', detail: 'Queued leads sync on the next run.', channel: 'system', sample: false } }];", (960, -220)),
         dt_insert("Log auto-off", "activity", (1200, -220)),
         note("## 06 · CRM retry queue\nEvery 2 minutes: leads marked **queued** (the CRM failed when they arrived) are sent again. "
              "Success → synced. Failure → stays queued, attempt count goes up. Upserts by email/id, so a retry never creates a duplicate.", (0, -480), 900, 200)]
    c = {}
    chain(c, "Outage switch", "Outage too old?", "Switch off", "Auto-off log", "Log auto-off")
    chain(c, "Every 2 minutes", "Outage switch", "Queued leads", "Pick", "CRM sync", "Results", "Patches", "Save lead")
    link(c, "Results", "Activity rows")
    link(c, "Activity rows", "Log activity")
    deploy("wf_retry", "06 CRM Retry Queue", n, c, settings={"saveDataSuccessExecution": "none"})


# =====================================================================================
# 07 Console API (read-only snapshot + the outage switch)
# =====================================================================================
def wf_console():
    n = [webhook("demo-dental/console", (0, 0)),
         if_true("Set outage?", "={{ $json.body.action === 'set_outage' }}", (240, 0)),
         code("Outage value", "return [{ json: { key: 'crm_outage', value: $('Webhook').first().json.body.on ? 'on' : 'off' } }];", (480, -200)),
         dt_update("Save switch", "settings", (720, -200), "key", "crm_outage", ["value"]),
         dt_get("Leads", "leads", (480, 0)),
         dt_get("Activity", "activity", (720, 0)),
         dt_get("Appointments", "appointments", (960, 0)),
         dt_get("Calls", "calls", (1200, 0)),
         dt_get("Settings", "settings", (1440, 0)),
         code("Snapshot", js(r"""
const rows = n => $(n).all().map(i => i.json).filter(r => Object.keys(r).length);
const strip = r => { const { id, createdAt, updatedAt, ...rest } = r; return rest; };
const leads = rows('Leads').map(strip).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
const activity = rows('Activity').map(strip).sort((a, b) => String(b.at).localeCompare(String(a.at))).slice(0, 400);
const appointments = rows('Appointments').map(strip).sort((a, b) => String(a.start).localeCompare(String(b.start)));
const calls = rows('Calls').map(strip).sort((a, b) => String(b.started_at).localeCompare(String(a.started_at))).slice(0, 100);
const settings = Object.fromEntries(rows('Settings').map(s => [s.key, s.value]));
return [{ json: { ok: true, server_time: new Date().toISOString(), crm: __HUBSPOT__ ? 'HubSpot' : 'Built-in CRM', outage: settings.crm_outage === 'on', leads, activity, appointments, calls } }];
"""), (1680, 0)),
         respond("Reply", "={{ JSON.stringify($json) }}", (1920, 0)),
         note("## 07 · Console API\nRead-only data for the demo console (leads, activity, bookings, calls) and the CRM-outage switch. "
              "The website reaches it only through its own server with a secret header.", (0, -440), 760, 180)]
    c = {}
    chain(c, "Webhook", "Set outage?")
    link(c, "Set outage?", "Outage value", 0)
    link(c, "Set outage?", "Leads", 1)
    link(c, "Outage value", "Save switch")
    link(c, "Save switch", "Leads")
    chain(c, "Leads", "Activity", "Appointments", "Calls", "Settings", "Snapshot", "Reply")
    deploy("wf_console", "07 Console API", n, c, settings={"saveDataSuccessExecution": "none"})


if __name__ == "__main__":
    webhook_cred()
    wf_errors()
    wf_save_lead()
    wf_crm_sync()
    wf_lead()
    wf_tools()
    wf_after_call()
    wf_chat()
    wf_comments()
    wf_retry()
    wf_console()
    print("webhook base:", api.__module__ and "set", "| HubSpot:", "on" if HUBSPOT else "off (built-in CRM)")
