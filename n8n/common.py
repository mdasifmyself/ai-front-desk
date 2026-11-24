"""Shared helpers for the Front Desk n8n build (the independent copy).

Settings live outside the project and are never printed:
  ~/.config/asif-demos/            n8n_url (the API, reached through an SSH tunnel), n8n_api_key,
                                   webhook_base (the public https address), openai_credential.json, elevenlabs_key
  ~/.config/asif-demos/frontdesk/  ids.json, webhook_secret, original_answer_engine_backup.json, hubspot_token.txt (optional)
The server is Asif's own (asif-demos-n8n). The original project and its server are never touched.
"""
import json, pathlib, urllib.request, urllib.error, uuid

ROOT = pathlib.Path(__file__).resolve().parent
SHARED = pathlib.Path.home() / ".config/asif-demos"
CFG = SHARED / "frontdesk"
CFG.mkdir(mode=0o700, parents=True, exist_ok=True)
N8N_URL = (SHARED / "n8n_url").read_text().strip()
N8N_KEY = (SHARED / "n8n_api_key").read_text().strip()
HOOK_BASE = (SHARED / "webhook_base").read_text().strip()          # https://…/webhook
OPENAI_CRED = json.loads((SHARED / "openai_credential.json").read_text())   # {"id": …, "name": …}
MODEL = "gpt-6-luna"
PREFIX = "Front Desk | "


def api(method, path, body=None, ok404=False):
    req = urllib.request.Request(N8N_URL + "/api/v1" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        if ok404 and e.code == 404:
            return None
        raise SystemExit(f"n8n API {method} {path} -> {e.code}: {e.read().decode()[:600]}")


def ids():
    f = CFG / "ids.json"
    return json.loads(f.read_text()) if f.exists() else {}


def save_ids(d):
    f = CFG / "ids.json"
    f.write_text(json.dumps(d, indent=2))
    f.chmod(0o600)
