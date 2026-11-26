import csv
import io
import math
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select, update

from . import ai, troubleshooting, repairs
from .analytics import overview
from .keepalive import lifespan
from .db import (
    DemoRoster,
    Agent,
    Article,
    Audit,
    Checklist,
    Escalation,
    Event,
    Recommendation,
    State,
    Ticket,
    now,
    session,
)
from .import_csv import DATA_DIR, read_csv
from .records import all_rows, current, event, filtered, filters, get_pair, retrieve
from .schemas import (
    ScriptApproval,
    CHECKS,
    AnalysisOut,
    ArticleIn,
    ArticleOut,
    CategoryMetrics,
    CheckIn,
    HandoffEvidence,
    Readiness,
    Decision,
    EscalationPage,
    Note,
    OverviewOut,
    Patch,
    Resolution,
    TicketOut,
    TicketPage,
)

app = FastAPI(title="RideOps Resolve", version="1.0", lifespan=lifespan)
DB = Depends(session)
FILTER = Depends(filters)


@app.middleware("http")
async def check_request_origin(request, call_next):
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and request.headers.get("sec-fetch-site") == "cross-site"
    ):
        return JSONResponse(
            {"detail": "Open this workspace to make changes."}, status_code=403
        )
    return await call_next(request)


@app.get("/health")
async def liveness():
    return {"status": "ok"}


@app.get("/api/health")
def health(db=DB):
    db.execute(select(1))
    return {"status": "ok"}


@app.get("/api/workspace")
def workspace(db=DB):
    rows = all_rows(db)
    return {
        "clients": sorted({r["client_name"] for r in rows}),
        "categories": sorted({r["category"] for r in rows}),
        "agents": list(db.scalars(select(Agent.name).order_by(Agent.name))),
        "priorities": ["P1", "P2", "P3", "P4"],
        "statuses": ["Open - with L1", "Open - with Engineering", "Closed"],
        "checks": CHECKS,
        "range": [
            min((r["created_at"][:10] for r in rows), default=None),
            max((r["created_at"][:10] for r in rows), default=None),
        ],
        "dictionary": read_csv(DATA_DIR / "rideops_data_dictionary.csv"),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "model": ai.configured_model(),
        "ticket_count": len(rows),
    }


@app.get("/api/tickets", response_model=TicketPage)
def tickets(
    q: str = "",
    escalation: Literal["", "Yes", "No"] = "",
    sort: Literal["newest", "oldest", "open-first"] = "newest",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    f=FILTER,
    db=DB,
):
    stmt = select(Ticket, State).join(State)
    fields = {
        "client_name": Ticket.client,
        "category": Ticket.category,
        "status": State.status,
        "priority": Ticket.original["priority"].as_string(),
    }
    for key, column in fields.items():
        if f[key]:
            stmt = stmt.where(column == f[key])
    if f["start"]:
        stmt = stmt.where(Ticket.created_at >= datetime.combine(f["start"], time.min))
    if f["end"]:
        stmt = stmt.where(Ticket.created_at <= datetime.combine(f["end"], time.max))
    if escalation:
        stmt = stmt.where(Ticket.original["escalated_to_eng"].as_string() == escalation)
    term = q.strip().lower()
    if term:
        stmt = stmt.where(
            or_(
                func.lower(Ticket.id).contains(term, autoescape=True),
                func.lower(Ticket.original["description"].as_string()).contains(
                    term, autoescape=True
                ),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = (
        (Ticket.created_at.desc(), Ticket.id.desc())
        if sort == "newest"
        else (Ticket.created_at, Ticket.id)
    )
    if sort == "open-first":
        order = (State.status == "Closed", Ticket.created_at, Ticket.id)
    items = [
        current(t, s)
        for t, s in db.execute(
            stmt.order_by(*order).offset((page - 1) * limit).limit(limit)
        )
    ]
    return {
        "items": items,
        "total": total,
        "pages": math.ceil(total / limit),
        "page": page,
    }


def latest(db, model, id):
    return db.scalar(
        select(model).where(model.ticket_id == id).order_by(model.id.desc()).limit(1)
    )


def article_json(a):
    return ArticleOut.model_validate(a).model_dump(mode="json")


@app.get("/api/tickets/{id}", response_model=TicketOut)
def detail(id: str, db=DB):
    ticket, state = get_pair(db, id)
    r = current(ticket, state)
    similar, articles = retrieve(db, r)
    check = db.get(Checklist, id)
    recommendation = latest(db, Recommendation, id)
    events = [
        {"kind": kind, "at": ticket.original[key], "text": "Imported ticket history"}
        for key, kind in [
            ("created_at", "Ticket created"),
            ("first_response_at", "First response"),
            ("first_closed_at", "First closure"),
            ("final_closed_at", "Final closure"),
        ]
        if ticket.original[key]
    ]
    events.extend(
        {"kind": e.kind, "text": e.text, "at": e.at.isoformat(" ")}
        for e in db.scalars(
            select(Event).where(Event.ticket_id == id).order_by(Event.id)
        )
    )
    decisions = [
        {
            "decision": e.decision,
            "at": e.at,
            "override_reason": e.override_reason,
            "handoff": e.handoff,
            "checks": e.checks,
        }
        for e in db.scalars(
            select(Escalation)
            .where(Escalation.ticket_id == id)
            .order_by(Escalation.id.desc())
        )
    ]
    results = check.results if check else {}
    review = troubleshooting.readiness(r, results)
    return dict(
        **r,
        repair=repairs.SCRIPT
        if repairs.matches(r)
        and db.get(DemoRoster, id)
        and state.status == "Open - with L1"
        and any(a.id == repairs.ARTICLE_ID for a in articles)
        else None,
        original=ticket.original,
        similar=similar,
        articles=[article_json(a) for a in articles],
        timeline=sorted(events, key=lambda e: e["at"], reverse=True),
        decisions=decisions,
        checks=check.checks if check else [],
        results=results,
        guide=troubleshooting.GUIDES.get(r["category"], troubleshooting.GENERIC),
        guidance=troubleshooting.guidance(r),
        readiness=review,
        prepared_handoff=troubleshooting.prepare_handoff(r, results, review),
        analysis=recommendation.result if recommendation else None,
    )


def update_status(db, t, s, new, reason):
    r = current(t, s)
    if s.status == new:
        return
    before = s.status
    changes = s.changes.copy()
    if new == "Closed":
        closed_at = now().isoformat(" ")
        changes.update(final_closed_at=closed_at, resolution=reason)
        if not r["first_closed_at"]:
            changes["first_closed_at"] = closed_at
    elif before == "Closed":
        changes.update(
            reopen_count=r["reopen_count"] + 1, final_closed_at="", resolution=""
        )
    if before == "Open - with Engineering" and new == "Open - with L1":
        changes["eng_outcome"] = "Returned to L1"
    s.status, s.changes = new, changes
    event(db, t.id, "Status updated", f"{before} → {new}. {reason}".strip())


@app.post("/api/tickets/{id}/run-script")
def run_script(id: str, body: ScriptApproval, db=DB):
    # SQLite ignores FOR UPDATE. Reserve its write transaction before reading the ticket.
    if db.get_bind().dialect.name == "sqlite":
        db.execute(
            update(State).where(State.ticket_id == id).values(status=State.status)
        )
    t, s = get_pair(db, id, True)
    article = db.get(Article, repairs.ARTICLE_ID)
    if (
        s.status != "Open - with L1"
        or not article
        or not article.approved
        or not repairs.matches(t.original)
        or not db.get(DemoRoster, id)
    ):
        raise HTTPException(409, "This repair is unavailable for this ticket.")
    analysis = latest(db, Recommendation, id)
    if not analysis or not any(
        source["id"] == repairs.ARTICLE_ID
        for source in analysis.result.get("sources", [])
    ):
        raise HTTPException(
            409, "Analyse the ticket and review the suggested procedure first."
        )
    success, message = repairs.refresh_cutoff(db, id)
    event(
        db,
        id,
        "Verified script" if success else "Verification failed",
        f"{body.script}. {message}",
    )
    if success:
        update_status(db, t, s, "Closed", message)
    db.commit()
    return {"verified": success, "message": message, "status": s.status}


@app.get("/api/backlog")
def backlog(db=DB):
    rows = [r for r in all_rows(db) if r["status"] != "Closed"]
    today = now().date()
    for r in rows:
        r["age_days"] = max(0, (today - date.fromisoformat(r["created_at"][:10])).days)
    return sorted(rows, key=lambda r: (r["priority"], r["created_at"]))


@app.patch("/api/tickets/{id}", response_model=TicketOut)
def patch(id: str, body: Patch, db=DB):
    t, s = get_pair(db, id, True)
    if body.return_outcome and (
        s.status != "Open - with Engineering" or body.status != "Open - with L1"
    ):
        raise HTTPException(
            422, "A return outcome requires returning an engineering-owned ticket to L1"
        )
    if not body.status and not body.assigned_agent:
        raise HTTPException(422, "Specify a status or agent")
    if body.status == "Open - with Engineering" and s.status != body.status:
        raise HTTPException(409, "Handoff preparation does not transfer ownership")
    if body.status == "Closed" and s.status != "Closed":
        raise HTTPException(409, "Record a resolution using the resolve action")
    if body.assigned_agent:
        if not db.get(Agent, body.assigned_agent):
            raise HTTPException(422, "Unknown agent")
        s.agent = body.assigned_agent
        event(db, id, "Assignment changed", s.agent)
    if body.status:
        update_status(db, t, s, body.status, body.return_outcome or "")
        if body.return_outcome:
            s.changes = {**s.changes, "eng_outcome": body.return_outcome}
    db.commit()
    return current(t, s)


@app.post("/api/tickets/{id}/notes", status_code=201)
def note(id: str, body: Note, db=DB):
    get_pair(db, id, True)
    event(db, id, "Internal note", body.text)
    db.commit()
    return {"saved": True}


@app.post("/api/tickets/{id}/resolve", response_model=TicketOut)
def resolve(id: str, body: Resolution, db=DB):
    t, s = get_pair(db, id, True)
    if s.status == "Closed":
        raise HTTPException(409, "Ticket is already closed")
    if body.engineering_outcome:
        if s.status != "Open - with Engineering":
            raise HTTPException(
                422, "Engineering outcomes require an engineering-owned ticket"
            )
        s.changes = {**s.changes, "eng_outcome": body.engineering_outcome}
        event(db, id, "Engineering outcome", body.engineering_outcome)
    update_status(db, t, s, "Closed", body.text)
    db.commit()
    return current(t, s)


@app.patch("/api/tickets/{id}/checklist", response_model=CheckIn)
@app.put("/api/tickets/{id}/checklist", response_model=CheckIn)
def checklist(id: str, body: CheckIn, request: Request, db=DB):
    t, _ = get_pair(db, id, True)
    if not set(body.results) <= set(
        troubleshooting.GUIDES.get(t.category, troubleshooting.GENERIC)
    ):
        raise HTTPException(422, "Unknown troubleshooting step")
    previous = db.get(Checklist, id)
    if request.method == "PATCH" and previous:
        body = CheckIn.model_validate(
            {
                "results": previous.results,
                "checks": previous.checks,
                **body.model_dump(exclude_unset=True),
            }
        )
    if body.results == (previous.results if previous else {}) and set(
        body.checks
    ) == set(previous.checks if previous else []):
        return body
    db.merge(Checklist(ticket_id=id, **body.model_dump()))
    event(
        db,
        id,
        "Checklist saved",
        f"{len(body.checks)} of 5 checks confirmed. {len(body.results)} troubleshooting results recorded.",
    )
    db.commit()
    return body


@app.post("/api/tickets/{id}/analyse", response_model=AnalysisOut)
def analyse(id: str, db=DB):
    t, s = get_pair(db, id)
    r = current(t, s)
    similar, articles = retrieve(db, r)
    check = db.get(Checklist, id)
    notes = list(
        db.scalars(
            select(Event.text)
            .where(Event.ticket_id == id, Event.kind == "Internal note")
            .order_by(Event.id.desc())
            .limit(8)
        )
    )
    response = ai.analyse(
        r,
        check.results if check else {},
        notes,
        similar,
        [article_json(a) for a in articles],
    )
    db.add(
        Recommendation(
            ticket_id=id,
            source=response.source,
            result=response.model_dump(mode="json"),
        )
    )
    event(db, id, "Analysis prepared", response.source)
    db.commit()
    return response


@app.put("/api/tickets/{id}/readiness", response_model=Readiness)
def prepare_review(id: str, body: HandoffEvidence, db=DB):
    ticket, state = get_pair(db, id, True)
    evidence = body.model_dump()
    if state.changes.get("handoff_evidence", {}) != evidence:
        state.changes = {**state.changes, "handoff_evidence": evidence}
        event(
            db, id, "Handoff evidence saved", "Local draft prepared for agent review."
        )
    check = db.get(Checklist, id)
    review = troubleshooting.readiness(
        current(ticket, state), check.results if check else {}
    )
    db.commit()
    return review


@app.post("/api/tickets/{id}/escalate", deprecated=True)
def escalate(id: str):
    raise HTTPException(410, "This workspace prepares handoffs for manual review.")


@app.post("/api/tickets/{id}/handoff")
def draft(id: str, body: Decision, db=DB):
    get_pair(db, id, True)
    check = db.get(Checklist, id)
    db.add(
        Escalation(
            ticket_id=id,
            handoff=body.handoff.model_dump(),
            decision="Draft",
            override_reason=body.override_reason,
            checks=check.checks if check else [],
        )
    )
    event(db, id, "Engineering handoff draft", body.handoff.reason_for_escalation)
    db.commit()
    return {"decision": "Draft"}


@app.get("/api/escalations", response_model=EscalationPage)
def escalations(
    group: Literal["all", "pending", "escalated", "returned", "engineering"] = "all",
    page: int = Query(1, ge=1),
    db=DB,
):
    drafts = {}
    for e in db.scalars(select(Escalation).order_by(Escalation.id)):
        drafts[e.ticket_id] = e.decision
    items = []
    counts = {"pending": 0, "escalated": 0, "returned": 0, "engineering": 0}
    for r in all_rows(db):
        tags = []
        if drafts.get(r["ticket_id"]) == "Draft" and r["status"] == "Open - with L1":
            tags.append("pending")
        if r["escalated_to_eng"] == "Yes":
            tags.append("escalated")
        if "returned to l1" in r["eng_outcome"].lower():
            tags.append("returned")
        if r["status"] == "Open - with Engineering":
            tags.append("engineering")
        for tag in tags:
            counts[tag] += 1
        if tags and (group == "all" or group in tags):
            at = r.get("escalated_at")
            items.append(
                dict(
                    **r,
                    groups=tags,
                    age_days=(now() - datetime.fromisoformat(at)).days
                    if at and "engineering" in tags
                    else None,
                )
            )
    items.sort(key=lambda r: r.get("escalated_at", r["created_at"]), reverse=True)
    return {
        "items": items[(page - 1) * 20 : page * 20],
        "total": len(items),
        "counts": counts,
    }


@app.get("/api/analytics/overview", response_model=OverviewOut)
def dashboard(f=FILTER, db=DB):
    rows = all_rows(db, baseline=True)
    latest_created = max((r["created_at"][:10] for r in rows), default=None)
    snapshot_date = (
        date.fromisoformat(latest_created) if latest_created else date.today()
    )
    return overview(filtered(rows, f), snapshot_date)


@app.get("/api/analytics/categories", response_model=list[CategoryMetrics])
def categories(f=FILTER, db=DB):
    return dashboard(f, db)["categories"]


@app.get("/api/analytics/export")
def export(f=FILTER, db=DB):
    data = categories(f, db)
    stream = io.StringIO()
    w = csv.DictWriter(
        stream,
        fieldnames=[
            "name",
            "total",
            "open",
            "resolved",
            "escalated",
            "returned",
            "returned_rate",
            "client_count",
            "engineering_open",
            "reopened",
            "escalation_rate",
            "reopen_rate",
            "csat",
            "rated",
            "resolution_hours",
            "impact",
        ],
    )
    w.writeheader()
    w.writerows(data)
    return Response(
        stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="rideops-category-performance.csv"'
        },
    )


@app.get("/api/knowledge", response_model=list[ArticleOut])
def knowledge(q: str = "", category: str = "", db=DB):
    return [
        a
        for a in db.scalars(select(Article).order_by(Article.updated_at.desc()))
        if (not category or a.category == category)
        and q.lower() in f"{a.title} {a.issue} {a.steps} {a.resolution}".lower()
    ]


def known_category(db, body):
    if not db.scalar(
        select(Ticket.id).where(Ticket.category == body.category).limit(1)
    ):
        raise HTTPException(422, "Unknown category")


@app.post("/api/knowledge", response_model=ArticleOut, status_code=201)
def create(body: ArticleIn, db=DB):
    known_category(db, body)
    article = Article(**body.model_dump())
    db.add(article)
    db.flush()
    db.add(Audit(action="Article created", subject=str(article.id)))
    db.commit()
    return article


@app.put("/api/knowledge/{id}", response_model=ArticleOut)
def edit(id: int, body: ArticleIn, db=DB):
    article = db.get(Article, id, with_for_update=True)
    if id == repairs.ARTICLE_ID:
        raise HTTPException(409, "The reviewed demo procedure is read-only.")
    if not article:
        raise HTTPException(404, "Article not found")
    known_category(db, body)
    for k, v in body.model_dump().items():
        setattr(article, k, v)
    db.add(Audit(action="Article edited", subject=str(id)))
    db.commit()
    return article


@app.delete("/api/knowledge/{id}", status_code=204)
def delete(id: int, db=DB):
    article = db.get(Article, id, with_for_update=True)
    if id == repairs.ARTICLE_ID:
        raise HTTPException(409, "The reviewed demo procedure is read-only.")
    if not article:
        raise HTTPException(404, "Article not found")
    db.delete(article)
    db.add(Audit(action="Article deleted", subject=str(id)))
    db.commit()
    return Response(status_code=204)


web_dir = Path(
    os.getenv("RIDEOPS_WEB_DIR", Path(__file__).resolve().parents[2] / "frontend/out")
)
if web_dir.is_dir():
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="workspace")
