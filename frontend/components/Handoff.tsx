"use client";
import { useRef, useState } from "react";
import type { Detail, Handoff, HandoffEvidence, Readiness } from "@/lib/types";
import { api } from "@/lib/api";
import { Button } from "./common";

import { CheckCircle2, CircleDashed, ClipboardCopy } from "lucide-react";

export const handoffFields: Record<keyof Handoff, string> = {
  issue_summary: "Issue summary",
  actual_behaviour: "Actual behaviour",
  expected_behaviour: "Expected behaviour",
  troubleshooting_completed: "Troubleshooting completed",
  results: "Recorded results",
  missing_information: "Missing information",
  reason_for_escalation: "Reason for escalation",
};

const fields: [keyof HandoffEvidence, string, string][] = [
  ["error", "Error or observed symptom", "Use the exact message, or describe what appeared."],
  [
    "reproduction",
    "Reproduction steps",
    "Include the affected record and time, or explain why reproduction is unavailable.",
  ],
  [
    "supporting_evidence",
    "Supporting evidence",
    "Reference the screenshot, log, or values you actually compared.",
  ],
  ["expected", "Expected behaviour (if known)", "What should the requester have seen?"],
  ["reason", "Reason for engineering review", "What remains unresolved after the L1 checks?"],
];
const emptyEvidence: HandoffEvidence = {
  error: "",
  reproduction: "",
  supporting_evidence: "",
  expected: "",
  reason: "",
};

export function EngineeringHandoff({
  ticket,
  toast,
}: {
  ticket: Detail;
  toast: (message: string) => void;
}) {
  const initial = ticket.handoff_evidence || emptyEvidence;
  const [values, setValues] = useState(initial);
  const [saved, setSaved] = useState(initial);
  const [review, setReview] = useState(ticket.readiness);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const summary = useRef<HTMLTextAreaElement>(null);
  const dirty = fields.some(([key]) => values[key] !== saved[key]);
  const recorded = review.items.filter((item) => item.recorded).length;
  async function prepare() {
    setBusy(true);
    setError("");
    try {
      const next = await api<Readiness>("tickets/" + ticket.ticket_id + "/readiness", "PUT", values);
      setSaved(values);
      setReview(next);
      toast("Evidence saved and handoff prepared");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(review.summary);
      toast("Handoff copied");
    } catch {
      summary.current?.focus();
      summary.current?.select();
      toast("Summary selected. Use your keyboard’s Copy command.");
    }
  }
  return (
    <>
      <section className="card">
        <div className="card-heading">
          <h2>Escalation readiness</h2>
          <span className={"badge " + (review.ready ? "green" : "amber")}>
            {review.ready ? "Ready for agent review" : "Missing information"} · {recorded}/
            {review.items.length}
          </span>
        </div>
        <p>Based on the ticket and saved observations. Review their accuracy before sharing.</p>
        <ul className="readiness-list">
          {review.items.map((item) => (
            <li key={item.label}>
              {item.recorded ? (
                <CheckCircle2 size={17} className="recorded" />
              ) : (
                <CircleDashed size={17} className="missing" />
              )}
              <div>
                <strong>{item.label}</strong>
                <small>
                  {item.recorded ? "Recorded" : "Missing"} · {item.detail}
                </small>
              </div>
            </li>
          ))}
        </ul>
      </section>
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          void prepare();
        }}
      >
        <h2>Collect handoff evidence</h2>
        <p>Use the Investigation tab to record troubleshooting results.</p>
        <div className="form-grid">
          {fields.map(([key, label, hint]) => (
            <label key={key} className="field">
              {label}
              <textarea
                rows={2}
                maxLength={8000}
                placeholder={hint}
                value={values[key]}
                disabled={busy}
                onChange={(e) => setValues({ ...values, [key]: e.target.value })}
              />
            </label>
          ))}
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="actions">
          <Button disabled={busy} variant="default">
            {busy ? "Preparing…" : "Generate handoff"}
          </Button>
          {dirty && <small>Unsaved evidence</small>}
        </div>
      </form>
      <section className="card">
        <div className="card-heading">
          <h2>Engineering handoff draft</h2>
          <Button disabled={dirty || busy} onClick={copy}>
            <ClipboardCopy size={16} />
            Copy summary
          </Button>
        </div>
        <p>
          {dirty
            ? "Generate the handoff to include your edits."
            : "Review and share manually. This draft stays in the support workspace."}
        </p>
        <textarea
          className="summary-text"
          aria-label="Engineering handoff draft"
          rows={11}
          ref={summary}
          readOnly
          value={review.summary}
        />
      </section>
    </>
  );
}
