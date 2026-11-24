"use client";
import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import type { Snapshot } from "@/lib/types";
import { Feed } from "./ui";
import { displayName } from "@/lib/format";

const FLOWS = [
  ["01", "Lead intake + AI qualification", "Website form → save first → OpenAI score and follow-up → CRM"],
  ["02", "Voice agent tools", "Function calls from the voice agent: free times, booking, CRM, callback"],
  ["03", "After-call processing", "Transcript → AI call note, outcome, stage, WhatsApp follow-up"],
  ["04", "Patient chat agent", "WhatsApp-ready chat with the same knowledge and booking rules"],
  ["05", "Comment filter", "Labels comments, replies only to real enquiries"],
  ["06", "CRM retry queue", "Every 2 minutes: resends leads the CRM missed"],
  ["07", "Console API", "Feeds this dashboard"],
  ["08", "Error alerts", "Any crash is logged and flagged"],
];

export default function Automations({ snap, now, reload, boost }: { snap: Snapshot; now: number; reload: () => void; boost: (ms?: number) => void }) {
  const [busy, setBusy] = useState(false);
  const queued = snap.leads.filter((l) => l.crm_status === "queued");
  const system = snap.activity.filter((a) => ["queue", "crm", "error"].includes(a.kind)).slice(0, 10);

  const toggle = async () => {
    setBusy(true);
    await fetch("/api/outage", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ on: !snap.outage }) }).catch(() => null);
    await reload();
    boost(180000);
    setBusy(false);
  };

  return (
    <>
      <div className="top">
        <div>
          <h1>Automations</h1>
          <p className="sub">Eight n8n workflows run this clinic. Turn the CRM off below and watch the safety net keep every lead.</p>
        </div>
      </div>
      <div className="grid2">
        <div className="stack">
          <section className="card">
            <div className="outage">
              <div>
                <h2 style={{ marginBottom: 4 }}><ShieldCheck size={18} /> Simulate a CRM outage</h2>
                <p className="muted">When on, the CRM “stops answering”. New leads are still saved first, marked as queued, and resent every 2 minutes. Turn it off and they sync by themselves, with no duplicates.</p>
              </div>
              <button className={`switch${snap.outage ? " on" : ""}`} role="switch" aria-checked={snap.outage} aria-label="Simulate CRM outage" onClick={toggle} disabled={busy} />
            </div>
            {snap.outage && <p className="note" style={{ marginTop: 12 }}>Outage is on. Send a test lead now: it will show “Queued · retrying”.</p>}
          </section>
          <section className="card">
            <h2>Retry queue <span className="muted">{queued.length} waiting</span></h2>
            {!queued.length && <p className="muted">Empty: every lead is in the CRM.</p>}
            {queued.map((l) => <p key={l.lead_id} style={{ fontSize: 14, marginBottom: 6 }}><span className="chip bad">Attempt {l.crm_attempts}</span> {displayName(l.name)} · <span className="muted">{l.crm_error}</span></p>)}
          </section>
          <section className="card">
            <h2>CRM and system log</h2>
            <Feed items={system} leads={snap.leads} now={now} />
          </section>
        </div>
        <div className="stack">
          <section className="card">
            <h2>The workflows</h2>
            <div className="flows">
              {FLOWS.map(([n, name, what]) => (
                <div className="flow" key={n}>
                  <span className="flow-n">{n}</span>
                  <div><b>{name}</b><p>{what}</p></div>
                  <span className="chip ok">Live</span>
                </div>
              ))}
            </div>
          </section>
          <section className="card">
            <h2>How it fits together</h2>
            <div className="arch">
              <span>Website form</span><i>→</i><span>n8n</span><i>→</i><span>OpenAI</span><i>→</i><span>CRM ({snap.crm})</span><i>→</i><span>ElevenLabs voice agent</span><i>→</i><span>Calendar</span><i>→</i><span>WhatsApp</span>
            </div>
            <p className="muted" style={{ marginTop: 12 }}>The CRM step is one adapter: HubSpot, Pipedrive and GoHighLevel take the same lead with a different field map.</p>
          </section>
        </div>
      </div>
    </>
  );
}
