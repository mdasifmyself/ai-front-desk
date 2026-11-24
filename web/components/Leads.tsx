"use client";
import { Plus, X, PhoneCall, Mail, Phone } from "lucide-react";
import type { Lead, Snapshot } from "@/lib/types";
import { TempChip, StageChip, CrmChip, Sample, Feed } from "./ui";
import { ago, dayTime, displayName, initials, mmss, cap } from "@/lib/format";

const tempColor = (t: string) => (t === "hot" ? "#d9480f" : t === "warm" ? "#d4a017" : "#9aa4b2");

export default function Leads({ snap, now, onOpen, onTestLead }: { snap: Snapshot; now: number; onOpen: (id: string) => void; onTestLead: () => void }) {
  const { leads } = snap;
  return (
    <>
      <div className="top">
        <div>
          <h1>Leads</h1>
          <p className="sub">Your CRM: {snap.crm}. Each lead is scored by AI the moment it arrives. Tap one to see its timeline.</p>
        </div>
        <div className="actions"><button className="btn primary" onClick={onTestLead}><Plus size={16} /> Send a test lead</button></div>
      </div>
      <section className="card">
        <table className="tbl">
          <thead><tr><th>Name</th><th>Needs</th><th>AI score</th><th>Stage</th><th>CRM</th><th>Arrived</th></tr></thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.lead_id} onClick={() => onOpen(l.lead_id)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(l.lead_id)}>
                <td><div className="who"><span className="avatar">{initials(l.name)}</span><div><b>{displayName(l.name)}</b><small>{l.source}</small></div></div></td>
                <td>{l.service}</td>
                <td><TempChip lead={l} /></td>
                <td><StageChip stage={l.stage} /></td>
                <td><CrmChip lead={l} /></td>
                <td className="muted">{ago(l.created_at, now)} <Sample on={l.sample} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="lead-cards">
          {leads.map((l) => (
            <button key={l.lead_id} className="row-btn" onClick={() => onOpen(l.lead_id)}>
              <div className="who"><span className="avatar">{initials(l.name)}</span>
                <div style={{ flex: 1, minWidth: 0 }}><b>{displayName(l.name)}</b><small>{l.service} · {ago(l.created_at, now)}</small></div>
                <TempChip lead={l} />
              </div>
            </button>
          ))}
        </div>
        {!leads.length && <p className="empty">No leads yet. Send a test lead to start.</p>}
      </section>
    </>
  );
}

export function LeadDrawer({ lead, snap, now, onClose, onCall }: { lead: Lead; snap: Snapshot; now: number; onClose: () => void; onCall: (l: Lead) => void }) {
  const acts = snap.activity.filter((a) => a.lead_id === lead.lead_id);
  const calls = snap.calls.filter((c) => c.lead_id === lead.lead_id);
  const appts = snap.appointments.filter((a) => a.lead_id === lead.lead_id);
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`Lead ${displayName(lead.name)}`}>
        <div className="drawer-head">
          <span className="avatar">{initials(lead.name)}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <b>{displayName(lead.name)}</b> <Sample on={lead.sample} />
            <div className="muted">{lead.source} · {ago(lead.created_at, now)}</div>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <div className="drawer-body">
          <section className="card">
            <div className="actions" style={{ marginBottom: 14 }}>
              <button className="btn primary" onClick={() => onCall(lead)} disabled={!lead.name}><PhoneCall size={16} /> Call with AI</button>
              <StageChip stage={lead.stage} /> <CrmChip lead={lead} />
            </div>
            <dl className="kv">
              <dt>Phone</dt><dd><Phone size={13} /> {lead.phone || "—"}</dd>
              <dt>Email</dt><dd><Mail size={13} /> {lead.email || "—"}</dd>
              <dt>Needs</dt><dd>{lead.service || "—"}</dd>
              {lead.message && <><dt>Message</dt><dd>{lead.message}</dd></>}
              <dt>CRM record</dt><dd>{lead.crm_id ? `${snap.crm} · ${lead.crm_id}` : lead.crm_error || "saving…"}</dd>
            </dl>
          </section>

          <section className="card">
            <h2>AI qualification</h2>
            {lead.temperature ? (
              <>
                <div className="who" style={{ gap: 14, marginBottom: 12 }}>
                  <TempChip lead={lead} />
                  <div className="bar"><span style={{ width: `${lead.score}%`, background: tempColor(lead.temperature) }} /></div>
                  {lead.urgency && <span className="chip">{cap(lead.urgency.replace("_", " "))}</span>}
                </div>
                <dl className="kv">
                  <dt>Intent</dt><dd>{lead.intent}</dd>
                  <dt>Summary</dt><dd>{lead.summary}</dd>
                  <dt>Next step</dt><dd>{lead.next_action}</dd>
                </dl>
              </>
            ) : <p className="muted">Scoring now…</p>}
          </section>

          {lead.followup && (
            <section className="card">
              <h2>Follow-up for WhatsApp</h2>
              <div className="wa">{lead.followup}<small>written by AI</small></div>
            </section>
          )}

          {(appts.length > 0 || calls.length > 0) && (
            <section className="card">
              <h2>Calls and visits</h2>
              {appts.map((a) => <p key={a.appt_id} style={{ marginBottom: 8 }}><span className={`chip ${a.status === "booked" ? "ok" : "cold"}`}>{a.status === "booked" ? "Booked" : "Cancelled"}</span> {a.service} · {dayTime(a.start)}</p>)}
              {calls.map((c) => <p key={c.call_id} style={{ marginBottom: 8 }}><span className="chip blue">{cap(c.direction)} call · {mmss(c.duration_secs)}</span> {c.outcome}: <span className="muted">{c.summary}</span></p>)}
            </section>
          )}

          <section className="card">
            <h2>Timeline</h2>
            <Feed items={acts} leads={snap.leads} now={now} showWho={false} />
          </section>
        </div>
      </aside>
    </>
  );
}
