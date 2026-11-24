"use client";
import { useState } from "react";
import { useData, query, date, categoryName } from "@/lib/api";
import type { Workspace, Filters, TicketPage } from "@/lib/types";
import { Title, FilterBar, SearchBox, Badge, Pages, Feedback, Empty } from "./common";

export function TicketQueue({ meta, resolving }: { meta: Workspace; resolving: boolean }) {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Filters>({});
  const [sort, setSort] = useState("open-first");
  const [page, setPage] = useState(1);
  const list = useData<TicketPage>(
    "tickets?" + query({ ...filters, q: search, sort, page: String(page) }),
  );
  return (
    <>
      <Title
        title={resolving ? "Choose a ticket to resolve" : "Tickets"}
        sub="Open a ticket to investigate the issue, record your checks, and decide the next step."
      />
      <section className="card queue">
        <div className="focus-filters" aria-label="Issue focus">
          {Object.entries({
            "All categories": "",
            "Roster & booking": "Roster / booking not syncing",
            "Live tracking / GPS": "Live tracking / GPS incorrect",
          }).map(([label, category]) => (
            <button
              key={label}
              aria-pressed={(filters.category || "") === category}
              onClick={() => {
                setFilters({ ...filters, category });
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="table-tools">
          <SearchBox
            value={search}
            placeholder="Search by ticket ID or description"
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
          />
          <div className="actions">
            <select
              aria-label="Ticket order"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
            >
              <option value="open-first">Open first · oldest first</option>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
            <select
              aria-label="Historical escalation"
              value={filters.escalation || ""}
              onChange={(e) => {
                setFilters({ ...filters, escalation: e.target.value });
                setPage(1);
              }}
            >
              <option value="">All escalations</option>
              <option value="Yes">Previously escalated</option>
              <option value="No">Never escalated</option>
            </select>
            <FilterBar
              meta={meta}
              filters={filters}
              set={(f) => {
                setFilters(f);
                setPage(1);
              }}
            />
          </div>
        </div>
        {!list.data ? (
          <Feedback error={list.error} reload={list.reload} />
        ) : (
          <>
            {list.data.total ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Ticket &amp; issue</th>
                      <th>Client</th>
                      <th>Priority</th>
                      <th>Owner</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.data.items.map((t) => (
                      <tr key={t.ticket_id}>
                        <td>
                          <a className="ticket-link" href={"#ticket/" + t.ticket_id}>
                            {t.ticket_id}
                          </a>
                          <div>{t.description}</div>
                          <small>
                            {categoryName(t.category)} · {date(t.created_at, true)}
                          </small>
                        </td>
                        <td>{t.client_name}</td>
                        <td>
                          <Badge value={t.priority} />
                        </td>
                        <td>{t.assigned_agent}</td>
                        <td>
                          <Badge value={t.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty text="No matching tickets. Try another search or clear the filters." />
            )}
            <Pages page={page} go={setPage} total={list.data.total} />
          </>
        )}
      </section>
    </>
  );
}
