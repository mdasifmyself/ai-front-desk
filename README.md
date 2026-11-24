# AI Front Desk · demo copy (v2)

An independent copy of the dental "AI Front Desk" demo, made on 24 Nov 2026 for the case study on asifmyself.xyz.
The original project and its live demo are not changed by anything here.

- Live: https://frontdesk.asifmyself.xyz (Vercel project `front-desk-demo`)
- `web/` Next.js console. v2 design: Apple-style system (system typeface, floating rail with labels, bottom tab bar on
  phones, sheets for forms, the "Ava" call card). Styles in `web/app/globals.css`.
- `n8n/` and `agent/`: the scripts that build the n8n workflows and the ElevenLabs agent.
- Local run: `npm --prefix web run dev` (port 3021). `web/node_modules` is a link to the original's folder to save disk.

Open work
1. Backend still shared with the original demo (same n8n workflows and tables). To separate it: an OpenAI API key for
   the site's own n8n, then run `n8n/build.py` against that server and point the Vercel settings at it.
2. Per-visitor sandbox before the case study links here: each visitor sees only their own test leads; no shared outage switch.
3. Fixed here, still present in the original: the Chat screen stayed in two columns on phones (inline style in `Inbox.tsx`).
