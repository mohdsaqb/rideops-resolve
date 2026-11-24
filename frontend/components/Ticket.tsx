"use client";
import { useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { api, useData, date, categoryName, nav } from "@/lib/api";
import type { Analysis, Detail, Workspace } from "@/lib/types";
import { Button, Badge, Feedback, Modal, Select } from "./common";
import { EngineeringHandoff, handoffFields } from "./Handoff";

type Props = { id: string; initial?: string; meta: Workspace; toast: (message: string) => void };
export function TicketDetail({ id, initial, meta, toast }: Props) {
  const detail = useData<Detail>("tickets/" + encodeURIComponent(id));
  if (!detail.data) return <Feedback error={detail.error} reload={detail.reload} />;
  return (
    <Ticket ticket={detail.data} initial={initial} meta={meta} toast={toast} reload={detail.reload} />
  );
}

function Related({ ticket, open }: { ticket: Detail; open: boolean }) {
  return (
    <details className="card" open={open || undefined}>
      <summary>Related knowledge and similar tickets</summary>
      {ticket.articles.map((a) => (
        <article key={a.id}>
          <h3>{a.title}</h3>
          <p>{a.issue}</p>
          <p>{a.steps}</p>
          <p>Approved resolution · {a.resolution || "None recorded"}</p>
        </article>
      ))}
      {!ticket.articles.length && (
        <p>
          No matching articles. <a href="#knowledge">Open knowledge base</a>
        </p>
      )}
      {ticket.similar.map((t) => (
        <article key={t.ticket_id}>
          <a className="ticket-link" href={"#ticket/" + t.ticket_id}>
            {t.ticket_id}
          </a>{" "}
          · {categoryName(t.category)}
          <p>{t.description}</p>
          <small>
            Engineering outcome · {t.eng_outcome || "None recorded"}
            <br />
            Resolution · {t.resolution || "No narrative recorded"}
          </small>
        </article>
      ))}
      {!ticket.similar.length && <p>No similar historical tickets.</p>}
    </details>
  );
}

function History({ ticket: t }: { ticket: Detail }) {
  return (
    <>
      <section className="card">
        <h2>Ticket information</h2>
        <dl>
          {Object.entries({
            Client: t.client_name,
            "Client tier": t.client_tier,
            Channel: t.channel,
            "Created (IST)": t.created_at,
            "Reopen count": t.reopen_count,
            CSAT: t.csat_score ?? "No rating",
            Resolution: t.resolution || "No resolution recorded",
            "Imported engineering ticket": t.original.eng_ticket_id || "None",
            "Imported engineering outcome": t.original.eng_outcome || "None",
            "Engineering handoffs": t.eng_handoffs,
            "Latest engineering outcome": t.eng_outcome || "None",
          }).map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </section>
      <section className="card">
        <h2>Ticket history</h2>
        {t.timeline.map((event, i) => (
          <article key={i}>
            <h3>{event.kind}</h3>
            <small>{event.at.slice(0, 16).replace("T", " ")} IST</small>
            <p>{event.text}</p>
          </article>
        ))}
      </section>
      {t.decisions.length > 0 && (
        <section className="card">
          <h2>Handoff decisions</h2>
          {t.decisions.map((item, i) => (
            <details key={i}>
              <summary>
                {item.decision} · {item.at.slice(0, 16).replace("T", " ")}
              </summary>
              <dl>
                {Object.entries(item.handoff).map(([k, v]) => (
                  <div key={k}>
                    <dt>{handoffFields[k as keyof typeof handoffFields]}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
              <p>Confirmed checks · {item.checks.join(", ") || "None"}</p>
              {item.override_reason && <p>Override reason · {item.override_reason}</p>}
            </details>
          ))}
        </section>
      )}
    </>
  );
}

type Operation = "Assign ticket" | "Add note" | "Resolve ticket" | "Reopen ticket" | "Return to L1";
function Ticket({
  ticket: t,
  initial,
  meta,
  toast,
  reload,
}: Omit<Props, "id"> & { ticket: Detail; reload: () => void }) {
  const [operation, setOperation] = useState<Operation | null>(null);
  const [text, setText] = useState("");
  const [agent, setAgent] = useState(t.assigned_agent);
  const [outcome, setOutcome] = useState("");
  const [results, setResults] = useState(t.results);
  const savedResults = useRef(t.results);
  const [analysis, setAnalysis] = useState(t.analysis);
  const [reply, setReply] = useState(t.analysis?.result.customer_response || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endpoint = "tickets/" + t.ticket_id;
  const tab =
    initial === "handoff"
      ? "handoff"
      : initial === "history" || initial === "details"
        ? "history"
        : "investigate";
  function open(action: Operation) {
    setText("");
    setOutcome("");
    setError("");
    setOperation(action);
  }
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function saveResults() {
    const observations = Object.fromEntries(Object.entries(results).filter(([, v]) => v.trim()));
    if (JSON.stringify(observations) === JSON.stringify(savedResults.current)) return;
    await api(endpoint + "/checklist", "PATCH", { results: observations });
    savedResults.current = observations;
  }
  async function analyse() {
    await saveResults();
    const next = await api<Analysis>(endpoint + "/analyse", "POST");
    setAnalysis(next);
    setReply(next.result.customer_response);
    toast("Analysis ready");
  }
  async function changeTab(next: string) {
    if (tab === "investigate" && next !== tab) await saveResults();
    if (next === "handoff" && tab !== "handoff") {
      reload();
    }
    nav("ticket", t.ticket_id, next);
  }
  async function commit() {
    if (tab === "investigate") await saveResults();
    switch (operation) {
      case "Assign ticket":
        await api(endpoint, "PATCH", { assigned_agent: agent });
        break;
      case "Add note":
        await api(endpoint + "/notes", "POST", { text });
        break;
      case "Resolve ticket":
        await api(endpoint + "/resolve", "POST", { text, engineering_outcome: outcome || undefined });
        break;
      case "Reopen ticket":
      case "Return to L1":
        await api(endpoint, "PATCH", { status: "Open - with L1", return_outcome: outcome || undefined });
        break;
    }
    setOperation(null);
    toast("Ticket updated");
    reload();
  }
  return (
    <>
      <a className="back" href="#tickets">
        All tickets
      </a>
      <header className="detail-title">
        <div className="actions">
          <strong>{t.ticket_id}</strong>
          <Badge value={t.priority} />
          <Badge value={t.status} />
        </div>
        <h1>{t.description}</h1>
        <p>
          {t.client_name} · {categoryName(t.category)} · {date(t.created_at, true)} · {t.assigned_agent}
        </p>
      </header>
      <div className="tabs" aria-label="Ticket sections">
        {Object.entries({
          investigate: "Investigation",
          handoff: "Handoff readiness",
          history: "History",
        }).map(([key, label]) => (
          <button
            key={key}
            disabled={busy}
            aria-current={key === tab ? "page" : undefined}
            onClick={() => perform(() => changeTab(key))}
          >
            {label}
          </button>
        ))}
      </div>
      {error && !operation && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {tab === "investigate" && (
        <>
          <section className="card">
            <div className="card-heading">
              <div>
                <h2>L1 investigation</h2>
                <p>These suggested checks guide your investigation. Record only what you observe.</p>
              </div>
              <Button disabled={busy} onClick={() => perform(analyse)}>
                <Sparkles size={16} />
                Analyse with AI
              </Button>
            </div>
            {analysis && (
              <div className="analysis">
                <small>
                  {analysis.source} · {analysis.detail}
                </small>
                <h3>Problem summary</h3>
                <p>{analysis.result.problem_summary}</p>
                <dl>
                  {Object.entries({
                    "Likely category": analysis.result.category,
                    "Priority assessment":
                      (analysis.result.priority || t.priority) + " · recorded ticket priority",
                    "Confirmed facts": analysis.result.confirmed_facts.join(" · "),
                    "Possible causes": analysis.result.possible_causes.join(" · ") || "None established",
                    "Missing information":
                      analysis.result.missing_information.join(" · ") || "Review collected evidence",
                  }).map(([label, v]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{v}</dd>
                    </div>
                  ))}
                </dl>
                <p>
                  <strong>Recommended action</strong> · {analysis.result.recommended_action}
                </p>
                {analysis.result.next_step && <p>{analysis.result.next_step}</p>}
              </div>
            )}
            {t.guide.map((step, i) => (
              <label className="field" key={step}>
                {i + 1}. {step}
                {t.guidance.checks[i] && <small>{t.guidance.checks[i]}</small>}
                <input
                  maxLength={8000}
                  placeholder="Record observed result"
                  value={results[step] || ""}
                  onChange={(e) => setResults({ ...results, [step]: e.target.value })}
                />
              </label>
            ))}
            <Button
              disabled={busy}
              onClick={() =>
                perform(async () => {
                  await saveResults();
                  toast("Troubleshooting saved");
                })
              }
            >
              Save results
            </Button>
          </section>
          <section className="card">
            <h2>Resolution decision</h2>
            <div className="decision-grid">
              <div>
                <h3>Resolve at L1</h3>
                <p>{t.guidance.resolve}</p>
              </div>
              <div>
                <h3>Involve engineering</h3>
                <p>{t.guidance.engineering}</p>
              </div>
            </div>
          </section>
          {analysis && (
            <details className="card">
              <summary>Customer response</summary>
              <textarea
                aria-label="Customer response"
                rows={4}
                value={reply}
                onChange={(e) => setReply(e.target.value)}
              />
              <Button
                onClick={() =>
                  perform(async () => {
                    await navigator.clipboard.writeText(reply);
                    toast("Response copied");
                  })
                }
              >
                Copy response
              </Button>
            </details>
          )}
          <Related ticket={t} open={initial === "knowledge"} />
        </>
      )}
      {tab === "handoff" && <EngineeringHandoff ticket={t} toast={toast} />}
      {tab === "history" && <History ticket={t} />}
      <div className="actions ticket-actions">
        <Button disabled={busy} onClick={() => open("Add note")}>
          Add note
        </Button>
        <Button disabled={busy} onClick={() => open("Assign ticket")}>
          Assign ticket
        </Button>
        {t.status === "Open - with Engineering" && (
          <Button disabled={busy} onClick={() => open("Return to L1")}>
            Return to L1
          </Button>
        )}
        {t.status === "Open - with L1" && tab !== "handoff" && (
          <Button disabled={busy} onClick={() => perform(() => changeTab("handoff"))}>
            Prepare handoff
          </Button>
        )}
        {t.status === "Closed" ? (
          <Button disabled={busy} onClick={() => open("Reopen ticket")}>
            Reopen ticket
          </Button>
        ) : (
          <Button variant="default" disabled={busy} onClick={() => open("Resolve ticket")}>
            Resolve ticket
          </Button>
        )}
      </div>
      {operation && (
        <Modal
          title={operation}
          close={() => {
            if (!busy) setOperation(null);
          }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void perform(commit);
            }}
          >
            {operation === "Assign ticket" ? (
              <Select label="Assigned agent" options={meta.agents} value={agent} onChange={setAgent} />
            ) : operation === "Resolve ticket" || operation === "Add note" ? (
              <label className="field">
                {operation === "Resolve ticket" ? "Resolution summary" : "Internal note"}
                <textarea
                  required
                  maxLength={8000}
                  rows={4}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </label>
            ) : (
              <p>Move {t.ticket_id} to the L1 queue?</p>
            )}
            {t.status === "Open - with Engineering" &&
              (operation === "Return to L1" || operation === "Resolve ticket") && (
                <Select
                  label="Engineering outcome (optional)"
                  all="Select outcome"
                  value={outcome}
                  onChange={setOutcome}
                  options={
                    operation === "Return to L1"
                      ? ["Config issue - returned to L1", "Insufficient info - returned to L1"]
                      : ["Fixed", "Duplicate of known issue", "Not a bug - how-to", "Not reproducible"]
                  }
                />
              )}
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <div className="actions end">
              <Button type="button" disabled={busy} onClick={() => setOperation(null)}>
                Cancel
              </Button>
              <Button variant="default" disabled={busy}>
                Confirm
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
