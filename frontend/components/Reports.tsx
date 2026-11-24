"use client";
import { useState } from "react";
import { AreaChart, Area, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { date, num, query, categoryName, useData } from "@/lib/api";
import type { Entry, Filters, Overview, Workspace } from "@/lib/types";
import { Button, Feedback, FilterBar, Title, Empty } from "./common";

function Trend({ data }: { data: Overview }) {
  const [period, setPeriod] = useState("monthly");
  return (
    <section className="card">
      <div className="card-heading">
        <div>
          <h2>Ticket volume</h2>
          <p>
            Grouped by creation date. Escalated counts include tickets that later went to engineering.
          </p>
        </div>
        <select aria-label="Trend interval" value={period} onChange={(e) => setPeriod(e.target.value)}>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
      {data.kpis.total ? (
        <>
          <div className="legend">
            <span>Total tickets</span>
            <span>Escalated</span>
          </div>
          <div className="plot">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={period === "weekly" ? data.weekly : data.monthly}
                margin={{ left: -20, right: 8 }}
              >
                <CartesianGrid vertical={false} stroke="#e4eae7" />
                <XAxis dataKey="date" tickFormatter={(d) => date(d)} tickLine={false} fontSize={12} />
                <YAxis allowDecimals={false} tickLine={false} fontSize={12} />
                <Tooltip labelFormatter={(d) => date(String(d), true)} />
                <Area
                  dataKey="total"
                  name="Total tickets"
                  stroke="#14786c"
                  fill="#d9eee6"
                  strokeWidth={2}
                  isAnimationActive={false}
                />
                <Area
                  dataKey="escalated"
                  name="Escalated"
                  stroke="#b58230"
                  fill="transparent"
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <Empty text="No tickets in this period" />
      )}
    </section>
  );
}
function Breakdown({ data }: { data: Overview }) {
  const [selected, setSelected] = useState("Tickets by category");
  const chart: Record<string, Entry[]> = {
    "Tickets by category": data.categories.map((c) => ({ name: c.name, value: c.total })),
    "Escalations by category": data.categories.map((c) => ({ name: c.name, value: c.escalated })),
    "Resolution hours by category": data.categories.flatMap((c) =>
      c.resolution_hours === null ? [] : [{ name: c.name, value: c.resolution_hours }],
    ),
    "CSAT by category": data.categories.flatMap((c) =>
      c.csat === null ? [] : [{ name: c.name, value: c.csat }],
    ),
    Priorities: data.priorities,
    Statuses: data.statuses,
    Clients: data.clients,
    "Engineering outcomes": data.outcomes,
  };
  const entries = chart[selected],
    max = Math.max(1, ...entries.map((r) => r.value));
  return (
    <section className="card">
      <div className="card-heading">
        <h2>Breakdown</h2>
        <select
          aria-label="Breakdown measure"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {Object.keys(chart).map((k) => (
            <option key={k}>{k}</option>
          ))}
        </select>
      </div>
      <div className="bars">
        {entries.map((r) => (
          <div key={r.name}>
            <div className="row between">
              <span>{categoryName(r.name)}</span>
              <b>{num(r.value)}</b>
            </div>
            <progress max={max} value={r.value} aria-label={r.name} />
          </div>
        ))}
      </div>
      {!entries.length && <Empty text="No observations" />}
    </section>
  );
}
function CategoryTable({ data }: { data: Overview }) {
  return (
    <section className="card">
      <h2>Category performance</h2>
      <p>
        Impact ranks volume, escalation rate, reopen rate, low CSAT and resolution time with equal
        weight.
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {[
                "Category",
                "Impact / 100",
                "Tickets",
                "Escalation rate",
                "Returned / escalated",
                "Reopen rate",
                "CSAT",
                "Resolution hours",
              ].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...data.categories]
              .sort((a, b) => b.impact - a.impact)
              .map((c) => (
                <tr key={c.name}>
                  <td>{categoryName(c.name)}</td>
                  <td>{c.impact}</td>
                  <td>{c.total}</td>
                  <td>{num(c.escalation_rate)}%</td>
                  <td>{c.returned_rate === null ? "—" : num(c.returned_rate) + "%"}</td>
                  <td>{num(c.reopen_rate)}%</td>
                  <td>{num(c.csat)}</td>
                  <td>{num(c.resolution_hours)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
export function Reports({ meta, showSettings }: { meta: Workspace; showSettings: boolean }) {
  const [filters, setFilters] = useState<Filters>({});
  const suffix = query(filters);
  const { data, error, reload } = useData<Overview>("analytics/overview?" + suffix);
  const k = data?.kpis;
  const percent = (v: number | null) => (v === null ? "—" : num(v) + "%");
  const metrics = k
    ? [
        ["Total tickets", num(k.total), num(k.client_count) + " distinct clients"],
        ["Open tickets", num(k.open), num(k.engineering_open) + " with engineering at data pull"],
        [
          "Engineering escalation rate",
          percent(k.escalation_rate),
          k.escalated + " of " + num(k.total) + " tickets",
        ],
        [
          "Returned escalation rate",
          percent(k.returned_rate),
          k.returned + " of " + k.escalated + " escalated tickets",
        ],
        ["Ticket reopen rate", percent(k.reopen_rate), k.reopened + " of " + num(k.total) + " tickets"],
        [
          "Average CSAT",
          k.csat === null ? "—" : k.csat.toFixed(2) + " / 5",
          num(k.rated) + " rated tickets",
        ],
      ]
    : [];
  return (
    <>
      <Title
        title="Operations dashboard"
        sub="Historical support performance at the CSV data pull. Local ticket edits are tracked in the queue."
      >
        <FilterBar meta={meta} filters={filters} set={setFilters} />
        <Button asChild>
          <a href={"/api/analytics/export?" + suffix} download>
            Export CSV
          </a>
        </Button>
      </Title>
      {!data ? (
        <Feedback error={error} reload={reload} />
      ) : (
        <>
          <div className="metrics dashboard-metrics">
            {metrics.map(([label, value, note]) => (
              <section className="metric" key={label}>
                <h2>{label}</h2>
                <strong>{value}</strong>
                <small>{note}</small>
              </section>
            ))}
          </div>
          <Trend data={data} />
          <section className="card">
            <h2>Operational insights</h2>
            <div className="insights">
              {data.insights.map((i) => (
                <div key={i.title}>
                  <h3>{i.title}</h3>
                  <p>{i.body}</p>
                </div>
              ))}
            </div>
            {!data.insights.length && <Empty text="No matching tickets" />}
          </section>
          <Breakdown data={data} />
          <CategoryTable data={data} />
        </>
      )}
      <details className="card" open={showSettings || undefined}>
        <summary>Workspace and data source</summary>
        <p>
          {num(meta.ticket_count)} imported tickets · {date(meta.range[0], true)} to{" "}
          {date(meta.range[1], true)} · Asia/Kolkata
        </p>
        <p>
          AI service ·{" "}
          {meta.groq_configured ? "Groq · " + meta.model : "Predefined rules (Groq key not configured)"}
        </p>
        <dl>
          {meta.dictionary.map((row) => (
            <div key={row.column}>
              <dt>{row.column}</dt>
              <dd>{row.description}</dd>
            </div>
          ))}
        </dl>
      </details>
    </>
  );
}
