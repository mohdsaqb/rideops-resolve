# RideOps Resolve

RideOps Resolve helps first-line support agents investigate employee transport tickets, find a reviewed procedure and decide whether to fix an issue or prepare an engineering handoff. The case study includes 1,444 historical tickets across 191 clients. Engineering received 486 tickets and returned 173 to L1.

[Open the hosted demo](https://rideops-resolve.onrender.com/)

## Try it locally

Install **Python 3.12+** and **Node.js 22 with npm**. From the project root, run:

```sh
python3 start-local
```

On Windows, use `py -3 start-local`. The launcher installs dependencies, builds the frontend, migrates and imports the database, then prints the address to open. The first run needs internet access. Press Ctrl+C to stop. Local work persists in `.rideops/rideops.db`.

For PostgreSQL, start Docker Desktop and run `docker compose up --build -d --wait`. Open [localhost:3000](http://localhost:3000). Run `docker compose down` to stop.

## Using the workspace

| Screen | What you can do |
|---|---|
| Dashboard | Inspect the historical category and priority distributions, recurring descriptions, escalation rates and CSV export. The open workload uses current ticket status, groups tickets by priority and flags tickets open seven days or longer. |
| Tickets | Search by ID or description. Filter by client, dates, priority, status, category and previous escalation. Open a ticket to see its history, internal notes and assignment. |
| Resolve Ticket | Choose a ticket and select **Analyse with AI**. Review its likely category, similar cases, missing evidence and source guides. Save observations, review an eligible repair, resolve manually or prepare and copy an engineering handoff. |
| Knowledge Bank | Search guides or create a draft. Record the symptom, checks, resolution and verification before approving it for use. The built-in demo procedure is read-only. |

### Try a verified repair

1. Open **Resolve Ticket**, search **SUP-11422**, open it and click **Analyse with AI**.
2. Open the linked **Refresh a demo roster cutoff** article to inspect its scope and verification. Return to the ticket.
3. Click **Review verified script**. **Approve and run** authorizes the predefined repair and closure if verification succeeds. The script copies the confirmed demo booking cutoff to the demo roster and reads the saved value back. Success records the result in history and closes the workspace ticket.
4. Repeat with **SUP-11438**. Its demo shift lacks a confirmed cutoff. The check explains the missing evidence and leaves the ticket open with L1. **Prepare handoff** lets the agent document the remaining questions.

The two operational shift records are illustrative fixtures linked to real case-study ticket IDs. The script updates only the local demo roster and ticket state. The original CSV and historical dashboard remain available for comparison. Knowledge article edits and model responses cannot supply executable code.

## Configuration

The default local workflow uses SQLite, keyword retrieval and category checklists. To use Groq, copy `.env.example` to `.env`, set `GROQ_API_KEY` and restart. `GROQ_MODEL` selects the model. Hosted deployments take these variables from the backend service environment. When Groq is unavailable the analysis identifies its rule-based source. PostgreSQL deployments can set `DATABASE_URL` to the database connection string.

For optional semantic retrieval, use Python 3.12 and install the following in the backend environment after the first local run:

```sh
.venv/bin/python -m pip install -r backend/requirements-semantic.txt
```

On Windows use `.venv\Scripts\python.exe`. Set `RIDEOPS_EMBEDDING_MODEL` in `.env` to the path of a downloaded Sentence Transformers model directory (for example, all-MiniLM-L6-v2) and restart. SQL stores the approved guides. The optional Chroma index ranks guides in the ticket category using local embeddings. Keyword matching is available when the model is unavailable. Analysis shows the retrieved guidance and source, or explains when no approved guide matched.

## Project layout

| Path | Purpose |
|---|---|
| `frontend/` | React, Next.js and TypeScript screens, charts and REST client |
| `backend/app/` | FastAPI, SQLAlchemy, analytics, Groq, retrieval and the predefined repair |
| `backend/migrations/` | Alembic database migrations |
| `backend/tests/`, `frontend/test-browser.cjs` | API and disposable-workspace browser tests |
| `data/` | Supplied ticket CSV and field dictionary |
| `start-local`, `Dockerfile`, `compose.yaml` | Local launcher and container deployment |
