import { useData } from "@/lib/api";
import type { Ticket } from "@/lib/types";
import { Feedback } from "./common";

export function Backlog() {
  const { data, error, reload } = useData<Ticket[]>("backlog");
  return (
    <section className="card">
      <h2>Open workload by priority</h2>
      <p>
        Current workspace · Review P1 and P2 first. Tickets open for seven days or longer are
        flagged.
      </p>
      {!data ? (
        <Feedback error={error} reload={reload} />
      ) : (
        ["P1", "P2", "P3", "P4"].map((priority) => {
          const tickets = data.filter((t) => t.priority === priority);
          return (
            <details key={priority} open={priority === "P1" || priority === "P2"}>
              <summary>
                {priority} · {tickets.length} open
              </summary>
              {tickets.length ? (
                tickets.map((t) => (
                  <p key={t.ticket_id}>
                    <a href={"#ticket/" + t.ticket_id}>{t.ticket_id}</a> · {t.description}
                    <small>
                      {" "}
                      · {t.age_days} days open{(t.age_days || 0) >= 7 && " · Review overdue"}
                    </small>
                  </p>
                ))
              ) : (
                <p>No open tickets.</p>
              )}
            </details>
          );
        })
      )}
    </section>
  );
}
