"""Shared helpers for the DEMO Dental n8n build.

Secrets: the n8n URL/key come from ~/.config/renata-assessment (the same n8n server);
everything new for this demo lives in ~/.config/crm-voice-demo. Nothing secret is printed.
The original Leave Policy workflows are only ever READ (to copy), never changed.
"""
import json, pathlib, urllib.request, urllib.error, uuid

ROOT = pathlib.Path(__file__).resolve().parent
OLD = pathlib.Path.home() / ".config/renata-assessment"
CFG = pathlib.Path.home() / ".config/crm-voice-demo"
CFG.mkdir(mode=0o700, exist_ok=True)
N8N_URL = (OLD / "n8n_url").read_text().strip()
N8N_KEY = (OLD / "n8n_api_key").read_text().strip()
OPENAI_CRED = {"id": "QkaebtX2OWefzo5s", "name": "OpenAI account"}
MODEL = "gpt-6-luna"
PREFIX = "DEMO Dental | "


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
