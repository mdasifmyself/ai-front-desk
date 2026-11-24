"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ConversationProvider } from "@elevenlabs/react";
import { LayoutDashboard, Users, PhoneCall, CalendarDays, MessagesSquare, Workflow, Plus, Stethoscope } from "lucide-react";
import type { CallTarget, Lead, Snapshot, Tab } from "@/lib/types";
import Overview from "./Overview";
import Leads, { LeadDrawer } from "./Leads";
import Calls from "./Calls";
import Bookings from "./Bookings";
import InboxView from "./Inbox";
import Automations from "./Automations";
import LeadForm from "./LeadForm";

const TABS: { id: Tab; label: string; short: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview", short: "Today", icon: LayoutDashboard },
  { id: "leads", label: "Leads", short: "Leads", icon: Users },
  { id: "calls", label: "AI calls", short: "Calls", icon: PhoneCall },
  { id: "bookings", label: "Bookings", short: "Visits", icon: CalendarDays },
  { id: "inbox", label: "Chat", short: "Chat", icon: MessagesSquare },
  { id: "automations", label: "Automations", short: "Flows", icon: Workflow },
];

export default function Console() {
  return (
    <ConversationProvider>
      <Shell />
    </ConversationProvider>
  );
}

function Shell() {
  const [tab, setTab] = useState<Tab>("overview");
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [loadError, setLoadError] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const [formOpen, setFormOpen] = useState(false);
  const [openLead, setOpenLead] = useState<string | null>(null);
  const [callTarget, setCallTarget] = useState<CallTarget>({ direction: "inbound" });
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const seen = useRef<Set<string> | null>(null);
  const fastUntil = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/snapshot", { cache: "no-store" });
      const d = await r.json();
      if (d.ok) {
        const keys = new Set<string>(d.activity.map((a: { at: string; title: string }) => a.at + a.title));
        if (seen.current) setFresh(new Set([...keys].filter((k) => !seen.current!.has(k))));
        seen.current = keys;
        setSnap(d);
        setLoadError("");
      } else setLoadError(d.error || "Could not load data.");
    } catch {
      setLoadError("Could not reach the server. Retrying…");
    }
  }, []);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      if (!document.hidden) await load();
      if (!alive) return;
      timer.current = setTimeout(tick, Date.now() < fastUntil.current ? 1500 : 7000);
    };
    tick();
    const clock = setInterval(() => setNow(Date.now()), 15000);
    return () => { alive = false; if (timer.current) clearTimeout(timer.current); clearInterval(clock); };
  }, [load]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpenLead(null); setFormOpen(false); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Poll every 1.5 s for a while after something happens (a new lead, a call, a chat message).
  const boost = useCallback((ms = 45000) => {
    fastUntil.current = Date.now() + ms;
    if (timer.current) clearTimeout(timer.current);
    const tick = async () => {
      await load();
      timer.current = setTimeout(tick, Date.now() < fastUntil.current ? 1500 : 7000);
    };
    tick();
  }, [load]);

  const leads = snap?.leads || [];
  const lead = useMemo(() => leads.find((l) => l.lead_id === openLead) || null, [leads, openLead]);
  const callLead = (l: Lead) => { setOpenLead(null); setFormOpen(false); setCallTarget({ direction: "outbound", lead: l, autoStart: true }); setTab("calls"); };
  const go = (t: Tab) => { setTab(t); window.scrollTo({ top: 0 }); };
  const counts: Partial<Record<Tab, number>> = { leads: leads.length, bookings: (snap?.appointments || []).filter((a) => a.status === "booked").length };

  const nav = (cls: string) => TABS.map((t) => (
    <button key={t.id} className={`navi${tab === t.id ? " on" : ""}`} onClick={() => go(t.id)} aria-current={tab === t.id ? "page" : undefined} aria-label={t.label}>
      <span className="ni"><t.icon size={cls === "side" ? 20 : 22} strokeWidth={tab === t.id ? 2.2 : 1.8} /></span>
      <span>{cls === "side" ? t.label : t.short}</span>
      {cls === "side" && counts[t.id] !== undefined && <span className="count">{counts[t.id]}</span>}
    </button>
  ));
  const brand = (
    <div className="brand">
      <span className="brand-mark"><Stethoscope size={18} /></span>
      <div><div className="brand-name">AI Front Desk</div><span className="demo-pill">Sample</span></div>
    </div>
  );

  return (
    <div className="app">
      <aside className="rail">
        <div className="rail-in">
          <div className="brand" title="AI Front Desk, demo">
            <span className="brand-mark"><Stethoscope size={22} /></span>
            <span className="demo-pill">Sample</span>
          </div>
          <nav aria-label="Sections" style={{ display: "contents" }}>{nav("side")}</nav>
          <div className="rail-foot">
            <button className="rail-add" onClick={() => setFormOpen(true)} aria-label="Send a test lead"><Plus size={22} /></button>
            <span>Test lead</span>
          </div>
        </div>
      </aside>
      <header className="mobile-head">
        {brand}
        <button className="btn primary sm" onClick={() => setFormOpen(true)}><Plus size={14} /> Test lead</button>
      </header>

      <main className="main">
        {loadError && !snap && <div className="card"><p className="muted">{loadError}</p></div>}
        {!snap && !loadError && <div className="card"><p className="muted">Loading live data from the automation server…</p></div>}
        {snap && tab === "overview" && <Overview snap={snap} now={now} fresh={fresh} onTestLead={() => setFormOpen(true)} onCall={() => { setCallTarget({ direction: "inbound" }); go("calls"); }} onOpenLead={setOpenLead} go={go} />}
        {snap && tab === "leads" && <Leads snap={snap} now={now} onOpen={setOpenLead} onTestLead={() => setFormOpen(true)} />}
        {snap && tab === "calls" && <Calls snap={snap} now={now} target={callTarget} setTarget={setCallTarget} boost={boost} reload={load} />}
        {snap && tab === "bookings" && <Bookings snap={snap} onOpenLead={setOpenLead} />}
        {snap && tab === "inbox" && <InboxView boost={boost} />}
        {snap && tab === "automations" && <Automations snap={snap} now={now} reload={load} boost={boost} />}
        {snap && <p className="note-foot">Sample dental clinic. Records marked “Sample” were added for the demo; everything you send is processed live.</p>}
      </main>
      <nav className="tabbar" aria-label="Sections">{nav("mobile")}</nav>

      {lead && snap && <LeadDrawer lead={lead} snap={snap} now={now} onClose={() => setOpenLead(null)} onCall={callLead} />}
      {formOpen && <LeadForm snap={snap} boost={boost} onClose={() => setFormOpen(false)} onCall={callLead} onOpen={(id) => { setFormOpen(false); setOpenLead(id); }} />}
    </div>
  );
}
