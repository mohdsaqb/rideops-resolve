export type Ticket = {
  ticket_id: string;
  client_name: string;
  client_id: string;
  client_tier: string;
  category: string;
  description: string;
  assigned_agent: string;
  created_at: string;
  priority: string;
  status: string;
  channel: string;
  reopen_count: number;
  csat_score: number | null;
  eng_outcome: string;
  eng_ticket_id: string;
  eng_handoffs: number;
  escalated_to_eng: string;
  resolution?: string;
  final_closed_at: string;
  age_days?: number | null;
  groups?: string[];
};
export type Article = {
  id: number;
  title: string;
  category: string;
  issue: string;
  steps: string;
  resolution: string;
  updated_at: string;
};
export type Handoff = Record<
  | "issue_summary"
  | "actual_behaviour"
  | "expected_behaviour"
  | "troubleshooting_completed"
  | "results"
  | "missing_information"
  | "reason_for_escalation",
  string
>;
export type Analysis = {
  source: string;
  detail: string;
  result: {
    problem_summary: string;
    problem_area: string;
    category: string;
    priority?: string;
    confirmed_facts: string[];
    possible_causes: string[];
    troubleshooting: string[];
    missing_information: string[];
    next_step?: string;
    recommended_action: string;
    customer_response: string;
    handoff: Handoff;
  };
};
export type HandoffEvidence = Record<
  "error" | "reproduction" | "supporting_evidence" | "expected" | "reason",
  string
>;
export type Readiness = {
  items: { label: string; recorded: boolean; detail: string }[];
  ready: boolean;
  summary: string;
};
export type Detail = Ticket & {
  guidance: { checks: string[]; resolve: string; engineering: string };
  readiness: Readiness;
  handoff_evidence?: HandoffEvidence;
  prepared_handoff: Handoff;
  similar: Ticket[];
  articles: Article[];
  guide: string[];
  results: Record<string, string>;
  checks: string[];
  original: Ticket;
  analysis: Analysis | null;
  timeline: { kind: string; at: string; text: string }[];
  decisions: {
    decision: string;
    at: string;
    override_reason: string;
    handoff: Handoff;
    checks: string[];
  }[];
};
export type Workspace = {
  clients: string[];
  categories: string[];
  priorities: string[];
  statuses: string[];
  agents: string[];
  checks: string[];
  range: string[];
  dictionary: { column: string; description: string }[];
  groq_configured: boolean;
  model: string;
  ticket_count: number;
};
export type Stats = {
  returned: number;
  returned_rate: number | null;
  engineering_open: number;
  client_count: number;
  total: number;
  open: number;
  resolved: number;
  escalated: number;
  reopened: number;
  escalation_rate: number | null;
  reopen_rate: number | null;
  csat: number | null;
  rated: number;
  resolution_hours: number | null;
};
export type Category = Stats & { name: string; impact: number };
export type Entry = { name: string; value: number };
export type Point = {
  date: string;
  total: number;
  escalated: number;
  resolved: number;
};
export type Overview = {
  oldest_open: Ticket[];
  kpis: Stats;
  categories: Category[];
  weekly: Point[];
  monthly: Point[];
  priorities: Entry[];
  statuses: Entry[];
  clients: Entry[];
  outcomes: Entry[];
  ageing: Entry[];
  insights: { title: string; body: string }[];
  baseline: Stats;
  range: string[];
};
export type Filters = Record<string, string>;
export type TicketPage = {
  items: Ticket[];
  total: number;
  pages: number;
  page: number;
};
