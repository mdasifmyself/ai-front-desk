"use client";
import { useEffect, useRef, useState } from "react";
import { useConversation } from "@elevenlabs/react";
import { PhoneCall, PhoneOff, Mic, MicOff, PhoneIncoming, PhoneOutgoing, Loader2, Wrench } from "lucide-react";
import type { CallTarget, Snapshot } from "@/lib/types";
import { Feed, Sample } from "./ui";
import { ago, displayName, initials, mmss, cap } from "@/lib/format";

type Line = { role: "agent" | "user"; message: string };
type Summary = { outcome: string; sentiment: string; summary: string; next_action: string; followup: string; booked: boolean };
const TOOL_LABEL: Record<string, string> = {
  check_availability: "Checked free times", book_appointment: "Booked the visit", find_booking: "Looked up bookings",
  cancel_appointment: "Cancelled a visit", save_caller_details: "Saved details to the CRM", request_callback: "Created a callback task", end_call: "Ended the call",
};

export default function Calls({ snap, now, target, setTarget, boost, reload }: {
  snap: Snapshot; now: number; target: CallTarget; setTarget: (t: CallTarget) => void; boost: (ms?: number) => void; reload: () => void;
}) {
  const [phase, setPhase] = useState<"idle" | "connecting" | "live" | "processing" | "done">("idle");
  const [lines, setLines] = useState<Line[]>([]);
  const [tools, setTools] = useState<{ name: string; error: boolean }[]>([]);
  const [err, setErr] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const ctx = useRef<{ leadId: string; direction: string; startedAt: string; convId: string; done: boolean } | null>(null);
  const linesRef = useRef<Line[]>([]);
  const toolsRef = useRef<string[]>([]);
  const scroller = useRef<HTMLDivElement>(null);

  const finish = async () => {
    const c = ctx.current;
    if (!c || c.done) return;
    c.done = true;
    setPhase("processing");
    const secs = Math.round((Date.now() - new Date(c.startedAt).getTime()) / 1000);
    try {
      const r = await fetch("/api/call-ended", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: c.convId, lead_id: c.leadId, direction: c.direction, started_at: c.startedAt, duration_secs: secs, transcript: linesRef.current, tools: toolsRef.current }),
      });
      const d = await r.json();
      if (d.ok) setSummary(d); else setErr(d.error || "The call summary is not ready. It will appear in the call history.");
    } catch { setErr("The call summary is not ready. It will appear in the call history."); }
    setPhase("done");
    reload();
    boost(20000);
  };

  const conv = useConversation({
    onConnect: ({ conversationId }) => { if (ctx.current) ctx.current.convId = conversationId; setPhase("live"); },
    onDisconnect: () => { finish(); },
    onMessage: (m) => {
      const role = (m.role === "agent" || m.source === "ai") ? "agent" : "user";
      const line = { role, message: m.message } as Line;
      linesRef.current = [...linesRef.current, line];
      setLines(linesRef.current);
    },
    onAgentToolResponse: (p) => {
      const t = p as { tool_name?: string; is_error?: boolean };
      if (!t.tool_name) return;
      toolsRef.current = [...toolsRef.current, t.tool_name];
      setTools((x) => [...x, { name: t.tool_name!, error: !!t.is_error }]);
      reload();
    },
    onError: (message) => setErr(typeof message === "string" ? message : "The call dropped."),
  });

  const start = async () => {
    if (phase === "connecting" || phase === "live" || phase === "processing") return;
    setErr(""); setSummary(null); setLines([]); setTools([]); setElapsed(0);
    linesRef.current = []; toolsRef.current = [];
    setPhase("connecting");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
    } catch {
      setErr("Please allow the microphone so you can talk to the AI receptionist."); setPhase("idle"); return;
    }
    const l = target.lead;
    const r = await fetch("/api/voice-session", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(target.direction === "outbound" && l ? { direction: "outbound", lead_id: l.lead_id, name: l.name, service: l.service, message: l.message } : { direction: "inbound" }),
    }).then((x) => x.json()).catch(() => ({ ok: false, error: "Could not start the call." }));
    if (!r.ok) { setErr(r.error); setPhase("idle"); return; }
    ctx.current = { leadId: r.leadId, direction: target.direction, startedAt: new Date().toISOString(), convId: "", done: false };
    boost(300000);
    try {
      conv.startSession({ signedUrl: r.signedUrl, dynamicVariables: r.dynamicVariables, connectionType: "websocket" });
    } catch { setErr("Could not connect the call."); setPhase("idle"); }
  };

  const end = () => { conv.endSession(); setTimeout(() => finish(), 1200); };

  useEffect(() => {
    if (target.autoStart) { setTarget({ ...target, autoStart: false }); start(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  useEffect(() => {
    if (phase !== "live") return;
    const t = setInterval(() => setElapsed(Math.round((Date.now() - new Date(ctx.current!.startedAt).getTime()) / 1000)), 1000);
    return () => clearInterval(t);
  }, [phase]);
  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight }); }, [lines]);

  const busy = phase === "connecting" || phase === "live" || phase === "processing";
  const lead = target.direction === "outbound" ? target.lead : undefined;
  const who = lead ? displayName(lead.name) : "You, as a new patient";
  const c = ctx.current;
  const actions = c ? snap.activity.filter((a) => a.lead_id === c.leadId && a.at >= c.startedAt && ["tool", "appointment", "crm", "task", "call", "followup"].includes(a.kind)) : [];
  const state = { idle: target.direction === "outbound" ? "Ready to call back" : "Ready: you call the clinic", connecting: "Connecting…", live: conv.isSpeaking ? `Ava is speaking · ${mmss(elapsed)}` : `Listening… · ${mmss(elapsed)}`, processing: "Call ended. AI is writing the CRM note…", done: "Call ended" }[phase];

  return (
    <>
      <div className="top">
        <div>
          <h1>AI calls</h1>
          <p className="sub">Ava, the AI receptionist, answers new patients, checks real free times and books the visit while you watch every action.</p>
        </div>
      </div>

      <div className="callgrid">
        <section className="card call-pick">
          <h2>Who is on the call</h2>
          <div className="pick">
            <button className={`row-btn${target.direction === "inbound" ? " on" : ""}`} disabled={busy} onClick={() => setTarget({ direction: "inbound" })}>
              <div className="who"><span className="avatar"><PhoneIncoming size={16} /></span><div><b>Call the clinic</b><small>You are a new patient calling in</small></div></div>
            </button>
            <p className="muted" style={{ margin: "10px 6px 4px" }}>Or let the AI call a lead back</p>
            {snap.leads.filter((l) => l.name).slice(0, 12).map((l) => (
              <button key={l.lead_id} className={`row-btn${lead?.lead_id === l.lead_id ? " on" : ""}`} disabled={busy} onClick={() => setTarget({ direction: "outbound", lead: l })}>
                <div className="who"><span className="avatar">{initials(l.name)}</span><div style={{ flex: 1, minWidth: 0 }}><b>{displayName(l.name)}</b><small>{l.service}{l.temperature ? ` · ${l.temperature} ${l.score}` : ""}</small></div></div>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="phone-card" style={{ padding: "8px 0 0" }}>
            <div className={`ring${phase === "live" ? " live" : ""}${conv.isSpeaking ? " speaking" : ""}`}>
              <span className="avatar">{lead ? initials(lead.name) : <PhoneCall size={22} />}</span>
            </div>
            <b style={{ fontSize: 18 }}>{who}</b>
            <p className="muted">{target.direction === "outbound" ? <><PhoneOutgoing size={13} /> AI calls back · {lead?.service}</> : <><PhoneIncoming size={13} /> Inbound call to DEMO Dental</>}</p>
            <p className="call-state" aria-live="polite">{state}</p>
            <div className="call-btns">
              {(phase === "idle" || phase === "done") && <button className="btn green lg" onClick={start}><PhoneCall size={18} /> {target.direction === "outbound" ? "Take the AI’s call" : "Start the call"}</button>}
              {phase === "connecting" && <button className="btn ghost lg" disabled><Loader2 size={18} className="spin" /> Connecting</button>}
              {phase === "live" && <>
                <button className="btn ghost lg" onClick={() => conv.setMuted(!conv.isMuted)} aria-pressed={conv.isMuted}>{conv.isMuted ? <MicOff size={18} /> : <Mic size={18} />} {conv.isMuted ? "Unmute" : "Mute"}</button>
                <button className="btn red lg" onClick={end}><PhoneOff size={18} /> End call</button>
              </>}
              {phase === "processing" && <button className="btn ghost lg" disabled><Loader2 size={18} className="spin" /> Saving the call</button>}
            </div>
            {err && <p className="err">{err}</p>}
          </div>
          <div className="transcript" ref={scroller} style={{ marginTop: 18 }} aria-live="polite">
            {!lines.length && <p className="note">{phase === "live" ? "Say hello. Try: “I’d like a cleaning on Thursday afternoon.”" : "The live transcript appears here. In production the AI dials the patient’s phone; in this demo the call runs in your browser, so use headphones if you can. Calls stop after 3 minutes."}</p>}
            {lines.map((l, i) => <div key={i} className={`bubble ${l.role === "agent" ? "ai" : "user"}`}><span className="by">{l.role === "agent" ? "Ava (AI)" : "Caller"}</span>{l.message}</div>)}
          </div>
        </section>

        <div className="stack">
          <section className="card">
            <h2>What the AI is doing</h2>
            {tools.length > 0 && <div className="actions" style={{ marginBottom: 10 }}>{tools.map((t, i) => <span key={i} className={`chip ${t.error ? "bad" : "purple"}`}><Wrench size={11} /> {TOOL_LABEL[t.name] || t.name}</span>)}</div>}
            {actions.length ? <Feed items={actions} leads={snap.leads} now={now} showWho={false} /> : <p className="muted">Each tool call shows here as it happens: free times found, the booking, the CRM update.</p>}
          </section>
          {summary && (
            <section className="card">
              <h2>After the call</h2>
              <div className="summary-grid">
                <div><small>Outcome</small>{summary.outcome}</div>
                <div><small>Sentiment</small>{cap(summary.sentiment)}</div>
              </div>
              <p style={{ fontSize: 14, marginBottom: 10 }}>{summary.summary}</p>
              <p className="muted" style={{ marginBottom: 10 }}>Next: {summary.next_action}</p>
              {summary.followup && <div className="wa">{summary.followup}<small>WhatsApp follow-up</small></div>}
            </section>
          )}
        </div>
      </div>

      <section className="card" style={{ marginTop: 16 }}>
        <h2>Call history</h2>
        <div className="hist">
          {snap.calls.map((k) => (
            <div className="hist-row" key={k.call_id}>
              <div className="hist-top">
                <span className="avatar">{initials(k.name)}</span>
                <b>{displayName(k.name)}</b>
                <span className="chip blue">{cap(k.direction)} · {mmss(k.duration_secs)}</span>
                <span className={`chip ${k.outcome === "Booked" ? "ok" : k.outcome === "Not interested" ? "cold" : ""}`}>{k.outcome}</span>
                <span className="muted">{ago(k.started_at, now)}</span> <Sample on={k.sample} />
              </div>
              <p style={{ fontSize: 14, color: "var(--text-2)" }}>{k.summary}</p>
              {!k.sample && k.call_id.startsWith("conv_") && (
                <details>
                  <summary>Recording and transcript</summary>
                  <audio controls preload="none" src={`/api/recording?id=${k.call_id}`} />
                  <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
                    {safeTurns(k.transcript).map((t, i) => <p key={i} style={{ fontSize: 13 }}><b>{t.role === "agent" ? "Ava" : "Caller"}:</b> {t.message}</p>)}
                  </div>
                </details>
              )}
            </div>
          ))}
          {!snap.calls.length && <p className="empty">No calls yet.</p>}
        </div>
      </section>
    </>
  );
}

function safeTurns(s: string): Line[] {
  try { const v = JSON.parse(s); return Array.isArray(v) ? v : []; } catch { return []; }
}
