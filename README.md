# AI Front Desk

A front desk for a dental clinic that runs itself: a voice agent answers calls and books real free times, every new
lead is scored in seconds, and the team sees the whole day on one screen.

- **Live:** https://frontdesk.asifmyself.xyz (a shared test space with a sample clinic; please use made-up details)
- **Case study:** https://asifmyself.xyz/case-studies/dental-ai-front-desk

## What it does

| Step | What happens |
|---|---|
| 1. A lead arrives | From the website form, a call or a chat. The record is saved **before** any AI runs. |
| 2. The lead is scored | A score from 0 to 100, hot / warm / cold, a one-line summary, the next action and a drafted follow-up. If the AI is unavailable, simple rules score it instead. |
| 3. The voice agent takes the call | "Ava" checks the clinic's own calendar, reads the booking back and books only after the caller says yes. |
| 4. The call becomes a note | Outcome, summary and next action are written for the team. A call counts as booked only if a booking was really created. |
| 5. The CRM stays in step | If the CRM stops answering, leads wait in a queue and are sent again every 2 minutes, without duplicates. |

The same clinic knowledge also answers chat messages and sorts social comments, so only real enquiries get a reply.

## Rules the AI cannot break

- Free times come from the calendar, never from a guess. A taken or past time is refused.
- No double booking, and no visits at lunch, on Sunday or within 30 minutes.
- Answers come from the clinic's fact sheet (`clinic.json`). If it isn't there, the agent creates a callback task.
- No diagnosis. Danger signs are sent to emergency services.

The agent talks; code decides.

## How it is built

| Part | Technology | Where |
|---|---|---|
| Console (web app) | Next.js, React, TypeScript | `web/` |
| Automations | n8n: 10 workflows built by code, 5 data tables | `n8n/build.py`, `n8n/setup_tables.py`, `n8n/seed.py` |
| Voice agent | ElevenLabs Conversational AI with 6 tools (check availability, book, find, cancel, save caller details, request callback) | `agent/setup_agent.py` |
| Language model | OpenAI, called only from n8n | `n8n/build.py` |
| Clinic facts | One file feeds the prompts and the screens | `clinic.json` |
| Hosting | Vercel (web), self-hosted n8n | |

The browser never talks to n8n or ElevenLabs directly. Every call goes through the web app's own server routes
(`web/app/api/*`), which add a secret header. The n8n server exposes only its webhook addresses.

### The 10 workflows

`01` Lead intake and AI qualification · `02` Voice agent tools · `03` After-call processing · `04` Patient chat agent ·
`05` Comment filter · `06` CRM retry queue · `07` Console API · `08` Error alerts · `10` Save lead (helper) ·
`11` CRM sync (helper)

### Cost and failure guards

- Each AI workflow has a daily ceiling (lead scoring 100, after-call notes 50, chat 200, comments 50). Over it, the
  workflow takes its "AI unavailable" path: rules score the lead, the chat asks the patient to try again later.
- A crashed run is written to the console's activity log. With an alerts workflow set (`alerts_workflow.json`), a
  crash, an OpenAI error or a reached ceiling also sends the team a short message: workflow, failed step and error
  line, never keys or patient details.

## Run it yourself

You need an n8n server (2.x, with the public API on), an OpenAI key saved as an n8n credential, and an ElevenLabs account.

1. Put the settings in `~/.config/asif-demos/` (file names are listed at the top of `n8n/common.py`). Nothing secret
   lives in this repository.
2. Build the back end:
   ```bash
   python3 n8n/setup_tables.py   # the data tables
   python3 n8n/build.py          # the workflows (creates or updates, then switches them on)
   python3 n8n/seed.py           # sample leads, calls and bookings
   python3 agent/setup_agent.py  # the voice agent and its tools
   ```
3. Run the console:
   ```bash
   cd web && npm install && npm run dev
   ```
   Settings for `web/.env.local` (names only): `N8N_WEBHOOK_BASE`, `DEMO_WEBHOOK_KEY`, `ELEVENLABS_API_KEY`,
   `ELEVENLABS_AGENT_ID`.

## Tests

- `test_api.sh <path> '<json>'` calls one workflow and prints the reply.
- `tests/text_call.mjs` and `tests/simulate_call.py` run a scripted call against the voice agent.

## Scope of this build

Calls run in the browser and the CRM is built in. A phone number, HubSpot (the connection is written, not yet tested
live), Google Calendar and WhatsApp connect at rollout. The clinic, its patients and its bookings are sample data.

---

© Md Asif. All rights reserved. · https://asifmyself.xyz · mdasifmyself@gmail.com
