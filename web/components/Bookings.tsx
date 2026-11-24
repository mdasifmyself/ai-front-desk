"use client";
import type { Snapshot } from "@/lib/types";
import { Sample } from "./ui";
import { dayKey, dayLabel, displayName, time } from "@/lib/format";
import clinic from "@/lib/clinic.json";

export default function Bookings({ snap, onOpenLead }: { snap: Snapshot; onOpenLead: (id: string) => void }) {
  const today = dayKey(new Date().toISOString());
  const list = snap.appointments.filter((a) => dayKey(a.start) >= today);
  const days = Array.from(new Set(list.map((a) => dayKey(a.start))));
  return (
    <>
      <div className="top">
        <div>
          <h1>Bookings</h1>
          <p className="sub">Booked by the AI on calls and in chat, straight into the clinic’s calendar. A taken time can never be booked twice.</p>
        </div>
      </div>
      <div className="grid2">
        <section className="card">
          <h2>Upcoming visits</h2>
          {!list.length && <p className="empty">No upcoming visits. Call the clinic and book one.</p>}
          {days.map((d) => (
            <div className="day" key={d}>
              <h3>{dayLabel(list.find((a) => dayKey(a.start) === d)!.start)}</h3>
              {list.filter((a) => dayKey(a.start) === d).map((a) => (
                <button key={a.appt_id} className={`row-btn appt${a.status === "cancelled" ? " cancelled" : ""}`} onClick={() => a.lead_id && onOpenLead(a.lead_id)}>
                  <span className="t">{time(a.start)}</span>
                  <span style={{ minWidth: 0 }}><b style={{ fontWeight: 500 }}>{displayName(a.name)}</b><br /><span className="muted">{a.service}</span></span>
                  <span style={{ textAlign: "right" }}><span className={`chip ${a.status === "booked" ? "ok" : "cold"}`}>{a.status === "booked" ? a.source : "Cancelled"}</span><br /><Sample on={a.sample} /></span>
                </button>
              ))}
            </div>
          ))}
        </section>
        <section className="card">
          <h2>Clinic rules the AI follows</h2>
          <dl className="kv">
            <dt>Hours</dt><dd>{clinic.hours_text}</dd>
            <dt>Slots</dt><dd>{clinic.slot_minutes}-minute visits; times come from this calendar, never from the AI’s guess</dd>
            <dt>Emergencies</dt><dd>Same-day slots offered; danger signs are sent to 911</dd>
            <dt>Changes</dt><dd>{clinic.policies[0]}</dd>
          </dl>
        </section>
      </div>
    </>
  );
}
