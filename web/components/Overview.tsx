"use client";
import { ArrowRight, Users, Timer, PhoneCall, CalendarCheck, AudioLines, ChevronRight } from "lucide-react";
import type { Snapshot, Tab } from "@/lib/types";
import { Feed, Sample } from "./ui";
import { dayLabel, dayTime, displayName, initials } from "@/lib/format";

const STAGES = [
  { id: "New", color: "#8e7bef" },
  { id: "Contacted", color: "#0a6cf0" },
  { id: "Booked", color: "#30b457" },
  { id: "Lost", color: "#c3c9d4" },
];

export default function Overview({ snap, now, fresh, onTestLead, onCall, onOpenLead, go }: {
  snap: Snapshot; now: number; fresh: Set<string>; onTestLead: () => void; onCall: () => void; onOpenLead: (id: string) => void; go: (t: Tab) => void;
}) {
  const { leads, activity, appointments, calls } = snap;
  const week = leads.filter((l) => now - new Date(l.created_at).getTime() < 7 * 86400000);
  // Speed to lead: seconds from the form to the AI's qualification, for website leads.
  const speeds = leads.map((l) => {
    const q = activity.find((a) => a.lead_id === l.lead_id && a.kind === "ai");
    return q ? (new Date(q.at).getTime() - new Date(l.created_at).getTime()) / 1000 : null;
  }).filter((s): s is number => s !== null && s >= 0 && s < 600);
  const avgSpeed = speeds.length ? Math.round(speeds.reduce((a, b) => a + b, 0) / speeds.length) : 0;
  const booked = leads.filter((l) => l.stage === "Booked").length;
  const rate = leads.length ? Math.round((booked / leads.length) * 100) : 0;
  const mins = Math.round(calls.reduce((a, c) => a + Number(c.duration_secs || 0), 0) / 60);
  const upcoming = appointments.filter((a) => a.status === "booked" && new Date(a.start).getTime() > now).slice(0, 5);
  const byStage = STAGES.map((s) => ({ ...s, n: leads.filter((l) => (l.stage || "New") === s.id).length }));

  return (
    <>
      <div className="top">
        <div>
          <h1>Today</h1>
          <p className="sub">{dayLabel(new Date(now).toISOString())} · DEMO Dental Clinic</p>
        </div>
        <span className="live"><i />Live · updates by itself</span>
      </div>

      <div className="ov">
        <section className="hero" aria-labelledby="hero-h">
          <div>
            <div className="hero-tags"><span><i />Live demo</span><span>Sample clinic</span></div>
            <h2 id="hero-h">Every enquiry answered. Every visit booked.</h2>
            <p className="hero-sub">Leads are scored, saved to the CRM and called back by AI, without anyone at the desk.</p>
          </div>
          <div className="hero-stats">
            <div className="hstat"><p className="l"><Users size={14} /> Leads this week</p><p className="n">{week.length}</p><p className="s">{leads.filter((l) => l.temperature === "hot").length} hot in total</p></div>
            <div className="hstat"><p className="l"><Timer size={14} /> First AI response</p><p className="n">{avgSpeed ? `${avgSpeed} s` : "—"}</p><p className="s">form sent to lead scored</p></div>
            <div className="hstat"><p className="l"><CalendarCheck size={14} /> Leads booked</p><p className="n">{rate}%</p><p className="s">{booked} of {leads.length} leads</p></div>
          </div>
        </section>

        <section className="ava" aria-labelledby="ava-h">
          <div className="orb" aria-hidden="true"><div className="orb-core" /><div className="orb-ic"><AudioLines size={40} strokeWidth={2.2} /></div></div>
          <div className="ava-id">
            <h2 id="ava-h">Ava</h2>
            <p className="ava-role">AI receptionist</p>
            <span className="ava-state"><i />Ready to take a call</span>
          </div>
          <div className="ava-btns">
            <button className="btn primary lg" onClick={onCall}><PhoneCall size={18} /> Call the clinic</button>
            <button className="btn ghost" onClick={onTestLead}>Send a test lead <ArrowRight size={16} /></button>
          </div>
          <div className="ava-foot">
            <div><b>{calls.length}</b><span>calls handled</span></div>
            <div><b>{mins} min</b><span>talked</span></div>
          </div>
        </section>

        <section className="card guide" aria-labelledby="guide-h">
          <h2 id="guide-h">Try the whole flow in 2 minutes</h2>
          <div className="steps">
            <div className="step"><span className="step-n">1</span><div><b>Send a test lead</b>Fill the clinic’s website form.</div></div>
            <div className="step"><span className="step-n">2</span><div><b>Watch the automation</b>AI scores it, saves it to the CRM and writes a follow-up.</div></div>
            <div className="step"><span className="step-n">3</span><div><b>Take the AI’s call</b>Talk to the receptionist and book a visit.</div></div>
          </div>
        </section>

        <section className="card ov-feed">
          <h2>Live activity</h2>
          <Feed items={activity.slice(0, 10)} leads={leads} now={now} fresh={fresh} />
        </section>

        <div className="ov-side">
          <section className="card">
            <h2>Pipeline</h2>
            <div className="pipe" role="img" aria-label={byStage.map((s) => `${s.id} ${s.n}`).join(", ")}>
              {byStage.map((s) => s.n > 0 && <span key={s.id} style={{ flex: s.n, background: s.color }} />)}
            </div>
            <div className="legend">{byStage.map((s) => <span key={s.id}><em><i style={{ background: s.color }} />{s.id}</em><b>{s.n}</b></span>)}</div>
          </section>
          <section className="card">
            <h2>Next visits</h2>
            {!upcoming.length && <p className="empty">No visits booked yet. Call the clinic and book one.</p>}
            {upcoming.map((a) => (
              <button key={a.appt_id} className="row-btn visit" onClick={() => onOpenLead(a.lead_id)}>
                <span className="avatar">{initials(displayName(a.name))}</span>
                <span><b>{displayName(a.name)}</b><small>{a.service}</small></span>
                <span className="when">{dayTime(a.start)} <Sample on={a.sample} /><ChevronRight size={16} color="#98a2b3" /></span>
              </button>
            ))}
            <button className="btn ghost sm" style={{ marginTop: 10 }} onClick={() => go("bookings")}>See all bookings</button>
          </section>
        </div>
      </div>
    </>
  );
}
