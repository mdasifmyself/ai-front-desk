"use client";
import {
  Sparkles, Database, MessageCircle, PhoneCall, CalendarCheck, Inbox, AlertTriangle, ListChecks, Wrench, UserPlus, RotateCw,
} from "lucide-react";
import type { Activity, Lead } from "@/lib/types";
import { ago, displayName } from "@/lib/format";

export const Sample = ({ on }: { on?: boolean }) => (on ? <span className="sample" title="Sample record added for the demo">Sample</span> : null);

export function TempChip({ lead }: { lead: Lead }) {
  if (!lead.temperature) {
    const fresh = Date.now() - new Date(lead.created_at).getTime() < 90 * 1000;
    return fresh && lead.source === "Website form"
      ? <span className="chip"><RotateCw size={12} className="spin" /> Scoring</span>
      : <span className="chip">Scored after the call</span>;
  }
  return <span className={`chip ${lead.temperature}`}>{lead.temperature[0].toUpperCase() + lead.temperature.slice(1)} · {lead.score}</span>;
}

export function StageChip({ stage }: { stage: string }) {
  const cls = stage === "Booked" ? "ok" : stage === "Lost" ? "cold" : stage === "Contacted" ? "blue" : "purple";
  return <span className={`chip ${cls}`}>{stage || "New"}</span>;
}

export function CrmChip({ lead }: { lead: Lead }) {
  if (lead.crm_status === "synced") return <span className="chip ok">In CRM</span>;
  if (lead.crm_status === "queued") return <span className="chip bad">Queued · retrying</span>;
  return <span className="chip">Saving…</span>;
}

const ICONS: Record<string, { icon: React.ElementType; cls: string }> = {
  lead: { icon: UserPlus, cls: "" },
  ai: { icon: Sparkles, cls: "ai" },
  crm: { icon: Database, cls: "ok" },
  queue: { icon: AlertTriangle, cls: "warn" },
  followup: { icon: MessageCircle, cls: "ok" },
  call: { icon: PhoneCall, cls: "" },
  appointment: { icon: CalendarCheck, cls: "ok" },
  chat: { icon: Inbox, cls: "" },
  task: { icon: ListChecks, cls: "warn" },
  tool: { icon: Wrench, cls: "ai" },
  error: { icon: AlertTriangle, cls: "bad" },
};

export function Feed({ items, leads, now, showWho = true, fresh }: { items: Activity[]; leads: Lead[]; now: number; showWho?: boolean; fresh?: Set<string> }) {
  if (!items.length) return <p className="empty">Nothing yet.</p>;
  const nameOf = (id: string) => { const l = leads.find((x) => x.lead_id === id); return l ? displayName(l.name) : id ? "Visitor" : "System"; };
  return (
    <div className="feed">
      {items.map((a, i) => {
        const m = ICONS[a.kind] || ICONS.lead;
        const Icon = m.icon;
        const key = a.at + a.title;
        return (
          <div className={`feed-row${fresh?.has(key) ? " fresh" : ""}`} key={key + i}>
            <span className={`fi ${m.cls}`}><Icon size={16} /></span>
            <div style={{ minWidth: 0 }}>
              <p className="feed-t">{a.title}</p>
              {a.detail && <p className="feed-d">{a.detail}</p>}
            </div>
            <div className="feed-who">
              {showWho && <div>{nameOf(a.lead_id)}</div>}
              <div>{ago(a.at, now)}</div>
              {a.sample && <Sample on />}
            </div>
          </div>
        );
      })}
    </div>
  );
}
