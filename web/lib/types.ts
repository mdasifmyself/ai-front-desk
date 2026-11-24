export type Lead = {
  lead_id: string; created_at: string; updated_at: string; name: string; phone: string; email: string;
  service: string; message: string; preferred_time: string; source: string; stage: string; score: number;
  temperature: string; intent: string; urgency: string; summary: string; next_action: string; followup: string;
  crm_status: string; crm_id: string; crm_attempts: number; crm_error: string; sample: boolean;
};
export type Activity = { lead_id: string; at: string; kind: string; title: string; detail: string; channel: string; sample: boolean };
export type Appointment = {
  appt_id: string; lead_id: string; name: string; phone: string; service: string; start: string; status: string;
  source: string; created_at: string; sample: boolean;
};
export type Call = {
  call_id: string; lead_id: string; name: string; direction: string; started_at: string; duration_secs: number;
  outcome: string; sentiment: string; summary: string; transcript: string; tools_used: string; sample: boolean;
};
export type Snapshot = {
  ok: boolean; server_time: string; crm: string; outage: boolean;
  leads: Lead[]; activity: Activity[]; appointments: Appointment[]; calls: Call[];
};
export type CallTarget = { direction: "inbound" | "outbound"; lead?: Lead; autoStart?: boolean };
export type Tab = "overview" | "leads" | "calls" | "bookings" | "inbox" | "automations";
