"use client";
import { useRef, useState, useEffect } from "react";
import { Send, Loader2, Sparkles } from "lucide-react";

type Msg = { role: "user" | "assistant"; content: string; tag?: string };
type Result = { index: number; label: string; reply_needed: boolean; reply: string; reason: string };

const SUGGEST = ["Do you take Cigna insurance?", "How much is teeth whitening?", "Any free times tomorrow afternoon?", "Do you do laser gum surgery?"];
const SAMPLE_COMMENTS = [
  { author: "Nadia R.", text: "How much is teeth whitening? Do you take Delta Dental?" },
  { author: "FollowerBoost", text: "Get 10k real followers today!!! DM us now" },
  { author: "Karim H.", text: "Best dentist in town, thank you Dr. Carter!" },
  { author: "Joy M.", text: "Waited 40 minutes past my appointment yesterday. Not happy." },
  { author: "Mike T.", text: "Who's watching the game tonight?" },
  { author: "Lena S.", text: "Can I book a check-up for my 7-year-old this Saturday?" },
];
const LABEL: Record<string, string> = { enquiry: "Enquiry", booking_request: "Booking request", complaint: "Complaint", praise: "Praise", spam: "Spam", off_topic: "Off-topic" };
const LABEL_CLS: Record<string, string> = { enquiry: "blue", booking_request: "ok", complaint: "warm", praise: "purple", spam: "bad", off_topic: "cold" };

export default function InboxView({ boost }: { boost: (ms?: number) => void }) {
  return (
    <>
      <div className="top">
        <div>
          <h1>Chat & comments</h1>
          <p className="sub">The same clinic knowledge answers WhatsApp messages and filters social comments, so only real enquiries get a reply.</p>
        </div>
      </div>
      <div className="grid2 inbox">
        <Chat boost={boost} />
        <Comments />
      </div>
    </>
  );
}

function Chat({ boost }: { boost: (ms?: number) => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "assistant", content: "Hi! I’m Ava from Lakeview Dental Clinic. Ask me anything, or book a visit right here." }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const leadId = useRef("L-W" + Date.now().toString(36).toUpperCase().slice(-5));
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" }); }, [msgs, busy]);

  const send = async (t: string) => {
    const message = t.trim();
    if (!message || busy) return;
    const history = msgs.slice(1).map(({ role, content }) => ({ role, content }));
    setMsgs((m) => [...m, { role: "user", content: message }]);
    setText(""); setBusy(true);
    const d = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lead_id: leadId.current, message, history }) })
      .then((r) => r.json()).catch(() => ({ ok: false }));
    const tag = d.booked ? "Booked in the calendar" : d.action === "check_availability" ? "Real free times from the calendar" : d.action === "request_callback" ? "Callback task created" : "";
    setMsgs((m) => [...m, { role: "assistant", content: d.reply || "Sorry, I could not answer just now. Please try again.", tag }]);
    setBusy(false);
    boost(15000);
  };

  return (
    <section className="card">
      <h2>WhatsApp chat <span className="muted">same AI, text channel</span></h2>
      <div className="phone">
        <div className="phone-top"><span className="avatar">LD</span><div><b style={{ fontWeight: 500 }}>Lakeview Dental Clinic</b><div style={{ fontSize: 12, opacity: 0.8 }}>{busy ? "typing…" : "AI assistant"}</div></div></div>
        <div className="phone-msgs" ref={box} aria-live="polite">
          {msgs.map((m, i) => <div key={i} className={`msg ${m.role === "user" ? "out" : "in"}`}>{m.content}{m.tag && <span className="tag">✓ {m.tag}</span>}</div>)}
          {busy && <div className="msg in"><Loader2 size={14} className="spin" /></div>}
        </div>
        <div className="phone-chips">{SUGGEST.map((s) => <button key={s} onClick={() => send(s)} disabled={busy}>{s}</button>)}</div>
        <form className="phone-in" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message" aria-label="Message" maxLength={600} />
          <button type="submit" aria-label="Send" disabled={busy}><Send size={18} /></button>
        </form>
      </div>
      <p className="muted" style={{ marginTop: 10 }}>In production this runs on the WhatsApp Cloud API: n8n receives each message by webhook and sends the reply back.</p>
    </section>
  );
}

function Comments() {
  const [list, setList] = useState(SAMPLE_COMMENTS);
  const [res, setRes] = useState<Result[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [mine, setMine] = useState("");

  const run = async (items = list) => {
    setBusy(true); setErr("");
    const d = await fetch("/api/comments", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ comments: items }) })
      .then((r) => r.json()).catch(() => ({ ok: false }));
    if (d.ok) setRes(d.results); else setErr(d.error || "The AI is busy. Please try again.");
    setBusy(false);
  };
  const add = () => {
    if (!mine.trim()) return;
    const next = [{ author: "You", text: mine.trim().slice(0, 300) }, ...list].slice(0, 10);
    setList(next); setMine(""); setRes(null); run(next);
  };
  const replies = res ? res.filter((r) => r.reply_needed).length : 0;

  return (
    <section className="card">
      <h2>Facebook comment filter</h2>
      <div className="actions" style={{ alignItems: "center", marginBottom: 6 }}>
        <button className="btn primary" onClick={() => run()} disabled={busy}>{busy ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />} {res ? "Run again" : "Let AI sort these comments"}</button>
        {res && <span className="muted">{replies} of {list.length} need a reply. The rest are ignored or hidden.</span>}
      </div>
      {err && <p className="err">{err}</p>}
      <div>
        {list.map((c, i) => {
          const r = res?.find((x) => x.index === i);
          return (
            <div className="cmt" key={i + c.text}>
              <div className="cmt-top"><b style={{ fontWeight: 500 }}>{c.author}</b>{r && <span className={`chip ${LABEL_CLS[r.label] || ""}`}>{LABEL[r.label] || r.label}</span>}{r && !r.reply_needed && <span className="muted">no reply: {r.reason}</span>}</div>
              <p style={{ fontSize: 14 }}>{c.text}</p>
              {r?.reply_needed && r.reply && <div className="cmt-reply"><b>AI reply</b>{r.reply}</div>}
            </div>
          );
        })}
      </div>
      <form className="field-row" onSubmit={(e) => { e.preventDefault(); add(); }}>
        <input value={mine} onChange={(e) => setMine(e.target.value)} placeholder="Write your own comment to test" aria-label="Your comment" maxLength={300} />
        <button className="btn ghost" type="submit" disabled={busy || !mine.trim()}>Test it</button>
      </form>
    </section>
  );
}
