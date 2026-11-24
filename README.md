# RideOps Resolve

RideOps Resolve helps first-line support agents investigate employee transport issues, from a booking missing from a shift roster to a cab showing the wrong location on a map. It brings the customer’s report, troubleshooting checks, and related cases into one place so the agent can decide whether to resolve the ticket or involve engineering.

In the case-study dataset, 486 of 1,444 tickets reached engineering. Of those, 173 came back to support, including 89 returned for insufficient information. RideOps focuses on that gap by showing agents which details are missing before they share a handoff. [Explore the tickets](data/rideops_support_tickets.csv) · [Field definitions](data/rideops_data_dictionary.csv)

## How it works

In ticket **SUP-11422**, a customer reports that the booking cutoff changed but the roster still uses the old cutoff.

1. **Understand the report.** The agent sees the reported symptom, the ticket’s priority, possible explanations, and a suggested first check.
2. **Investigate the mismatch.** The agent compares the booking and roster for the same shift, checks the employee mapping and sync time, and records what each check showed.
3. **Choose the next action.** If the requester confirms the correct entry is visible, the agent can record a resolution. If the mismatch persists, the app highlights missing evidence and prepares a summary the agent can review and copy for engineering.

## Features

- **Searchable ticket queue** with filters for client, category, priority, and status.
- **Guided investigation** with category-specific checks and optional Groq analysis. Built-in rules work without an API key.
- **Reusable knowledge** through searchable articles, similar tickets, and recorded resolutions.
- **Handoff readiness** based on documented symptoms, reproduction steps, troubleshooting results, and supporting evidence.
- **Operations dashboard** with ticket trends, escalation and return rates, reopens, and customer satisfaction, calculated from the imported records.

## Try it locally

Install **Python 3.12+** and **Node.js 22 with npm**. Clone this repository or download and unzip it, then open a terminal in the folder containing this README.

```sh
python3 start-local
```

On Windows, use `py -3 start-local`. Open the address printed in the terminal, usually [localhost:3000](http://127.0.0.1:3000). Search for **SUP-11422** to explore the roster case or **SUP-11429** for a GPS case. Press **Ctrl+C** to stop. Saved work is available the next time the app starts.

Built with Next.js, React, TypeScript, and FastAPI. The local launcher uses SQLite, and the Docker deployment uses PostgreSQL.
