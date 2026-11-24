import re
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select

from .retrieval import ranked_articles
from .db import Audit, Event, State, Ticket


def current(ticket, state, baseline=False):
    r = ticket.original.copy()
    if not baseline:
        r.update(state.changes, assigned_agent=state.agent, status=state.status)
    r["reopen_count"] = int(r["reopen_count"])
    r["eng_handoffs"] = int(r["eng_handoffs"])
    r["csat_score"] = int(r["csat_score"]) if r["csat_score"] else None
    return r


def all_rows(db, baseline=False):
    return [
        current(t, s, baseline)
        for t, s in db.execute(select(Ticket, State).join(State))
    ]


def get_pair(db, id, lock=False):
    query = select(Ticket, State).join(State).where(Ticket.id == id)
    row = db.execute(query.with_for_update() if lock else query).first()
    if not row:
        raise HTTPException(404, "Ticket not found")
    return row


def filters(
    client: str = "",
    category: str = "",
    status: str = "",
    priority: str = "",
    start: date | None = None,
    end: date | None = None,
):
    if start and end and start > end:
        raise HTTPException(422, "Start date must precede the end date")
    return {
        "client_name": client,
        "category": category,
        "status": status,
        "priority": priority,
        "start": start,
        "end": end,
    }


def filtered(rows, f):
    return [
        r
        for r in rows
        if all(
            not f[k] or r[k] == f[k]
            for k in ("client_name", "category", "status", "priority")
        )
        and (not f["start"] or r["created_at"][:10] >= str(f["start"]))
        and (not f["end"] or r["created_at"][:10] <= str(f["end"]))
    ]


def event(db, id, kind, description):
    db.add(Event(ticket_id=id, kind=kind, text=description))
    db.add(Audit(action=kind, subject=id))


def retrieve(db, ticket):
    def tokens(text):
        return set(re.findall(r"[a-z0-9]+", text.lower())) - {
            "the",
            "with",
            "for",
            "and",
            "not",
            "but",
            "from",
        }

    terms = tokens(ticket["description"])

    def rank(description, category):
        match = tokens(description)
        return len(terms & match) / max(1, len(terms | match)) + 0.25 * (
            category == ticket["category"]
        )

    history = [
        (rank(r["description"], r["category"]), r)
        for r in all_rows(db)
        if r["ticket_id"] != ticket["ticket_id"]
        and r["created_at"] <= ticket["created_at"]
    ]
    history.sort(key=lambda pair: (pair[0], pair[1]["created_at"]), reverse=True)
    return [r for score, r in history[:5] if score > 0.25], ranked_articles(db, ticket)
