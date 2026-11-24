"use client";
import { useState } from "react";
import { X, Check, Loader2, PhoneCall, AlertTriangle } from "lucide-react";
import type { Lead, Snapshot } from "@/lib/types";
import clinic from "@/lib/clinic.json";

const EXAMPLE = { name: "Alex Morgan", phone: "+1 415 555 0142", email: "alex.morgan@example.com", service: "Teeth whitening", message: "My wedding is in 3 weeks and I want whiter teeth. Do you have anything this week?", preferred_time: "This week, after 4 PM" };

export default function LeadForm({ snap, boost, onClose, onCall, onOpen }: {
  snap: Snapshot | null; boost: (ms?: number) => void; onClose: () => void; onCall: (l: Lead) => void; onOpen: (id: string) => void;
}) {
  const [f, setF] = useState({ name: "", phone: "", email: "", service: clinic.services[0].name, message: "", preferred_time: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [leadId, setLeadId] = useState("");
  const [sentAt, setSentAt] = useState(0);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr("");
    const t0 = Date.now();
    const d = await fetch("/api/lead", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(f) })
      .then((r) => r.json()).catch(() => ({ ok: false, error: "Could not send. Please try again." }));
    setBusy(false);
    if (!d.ok) { setErr(d.error || "Please check the form."); return; }
    setSentAt(t0); setLeadId(d.lead_id); boost(60000);
  };

  const lead = snap?.leads.find((l) => l.lead_id === leadId);
  const acts = snap?.activity.filter((a) => a.lead_id === leadId) || [];
  const secs = (kind: string) => { const a = acts.find((x) => x.kind === kind); return a && sentAt ? `${Math.max(1, Math.round((new Date(a.at).getTime() - sentAt) / 1000))} s` : ""; };
  const steps = [
    { done: !!lead, title: "Saved to the database first", sub: lead ? `Lead ${lead.lead_id} · nothing can be lost now` : "" },
    { done: !!lead?.temperature, title: "AI qualified the lead", sub: lead?.temperature ? `${lead.temperature} · ${lead.score}/100 · ${lead.intent} · ${secs("ai")}` : "" },
    { done: lead?.crm_status === "synced", warn: lead?.crm_status === "queued", title: lead?.crm_status === "queued" ? "CRM is down: kept safe in the retry queue" : `Saved to the CRM (${snap?.crm || "CRM"})`, sub: lead?.crm_id ? `Record ${lead.crm_id}` : lead?.crm_error || "" },
    { done: !!lead?.followup, title: "WhatsApp follow-up written", sub: lead?.followup || "" },
  ];
  const finished = steps.every((s) => s.done || s.warn);

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal="true" aria-label="Send a test lead">
        <div className="modal-head">
          <div>
            <h2>{leadId ? "Your lead is moving" : "Book a visit at Lakeview Dental"}</h2>
            <p className="muted">{leadId ? "Live from n8n. No one at the clinic touched this." : "This is the clinic’s website form. Please use made-up details: this test space is shared, so other visitors can see the leads."}</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        {!leadId && (
          <form onSubmit={submit}>
            <div className="form">
              <label>Full name<input required value={f.name} onChange={set("name")} autoComplete="off" maxLength={80} /></label>
              <label>Phone<input required value={f.phone} onChange={set("phone")} inputMode="tel" autoComplete="off" maxLength={30} /></label>
              <label>Email<input type="email" value={f.email} onChange={set("email")} autoComplete="off" maxLength={120} /></label>
              <label>What do you need?<select value={f.service} onChange={set("service")}>{clinic.services.map((s) => <option key={s.name}>{s.name}</option>)}</select></label>
              <label className="full">Message<textarea value={f.message} onChange={set("message")} maxLength={500} placeholder="Tell us a little about it" /></label>
              <label className="full">Best time for you<input value={f.preferred_time} onChange={set("preferred_time")} maxLength={80} placeholder="e.g. Thursday afternoon" /></label>
            </div>
            {err && <p className="err">{err}</p>}
            <div className="actions" style={{ marginTop: 16, justifyContent: "space-between" }}>
              <button type="button" className="btn ghost" onClick={() => setF({ ...EXAMPLE })}>Fill with an example</button>
              <button type="submit" className="btn primary lg" disabled={busy}>{busy ? <Loader2 size={16} className="spin" /> : null} Send request</button>
            </div>
          </form>
        )}

        {leadId && (
          <>
            <div className="progress" aria-live="polite">
              {steps.map((s, i) => {
                const running = !s.done && !s.warn && steps.slice(0, i).every((p) => p.done || p.warn);
                return (
                  <div key={i} className={`pstep${s.done ? " done" : s.warn ? " warn" : running ? " run" : ""}`}>
                    <span className="dot">{s.done ? <Check size={14} /> : s.warn ? <AlertTriangle size={13} /> : running ? <Loader2 size={13} className="spin" /> : i + 1}</span>
                    <div style={{ minWidth: 0 }}><b style={{ fontWeight: 500 }}>{s.title}</b>{s.sub && <small>{s.sub}</small>}</div>
                  </div>
                );
              })}
            </div>
            {finished && lead ? (
              <>
                <p className="note" style={{ marginBottom: 14 }}>Next, the AI calls the lead back. In production it dials their phone within a minute; here the call rings in your browser.</p>
                <div className="actions" style={{ justifyContent: "space-between" }}>
                  <button className="btn ghost" onClick={() => onOpen(lead.lead_id)}>Open the lead</button>
                  <button className="btn green lg" onClick={() => onCall(lead)}><PhoneCall size={18} /> Take the AI’s call</button>
                </div>
              </>
            ) : <p className="muted">Usually takes 5 to 10 seconds.</p>}
          </>
        )}
      </div>
    </>
  );
}
