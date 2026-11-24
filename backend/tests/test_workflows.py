"""Exercise real CSV records in a temporary database, through FastAPI's public API."""

import csv
import io
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import ai, db, import_csv
from app.db import Audit, Ticket
from app.main import app
from app.schemas import CHECKS


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + str(tmp_path / "workflow.db"))
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(import_csv, "Session", factory)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    command.upgrade(
        Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head"
    )
    imported = import_csv.run()
    assert imported > 0 and import_csv.run() == 0

    def dependency():
        with factory() as conn:
            yield conn

    app.dependency_overrides[db.session] = dependency
    with TestClient(app) as c:
        yield c, factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize("ticket_id", ["SUP-11422", "SUP-11429"])
def test_complete_investigation(client, ticket_id):
    c, factory = client
    path = "/api/tickets/" + ticket_id
    ticket = c.get(path).json()
    meta = c.get("/api/workspace").json()
    assert (
        c.get(
            "/api/tickets", params={"q": ticket_id, "category": ticket["category"]}
        ).json()["total"]
        == 1
    )
    assert all(r["ticket_id"] != ticket_id for r in ticket["similar"])
    assert ticket["readiness"]["ready"] is False
    assert sum(item["recorded"] for item in ticket["readiness"]["items"]) == 2
    rec = c.post(path + "/analyse").json()
    assert rec["source"] == "Predefined rules"
    assert rec["result"]["priority"] == ticket["priority"]
    assert rec["result"]["category"] == ticket["category"]
    assert rec["result"]["troubleshooting"] == ticket["guide"]
    assert len(ticket["guidance"]["checks"]) == len(ticket["guide"])
    assert (
        c.post(
            path + "/notes", json={"text": "Evidence collection started."}
        ).status_code
        == 201
    )
    agent = next(a for a in meta["agents"] if a != ticket["assigned_agent"])
    assert c.patch(path, json={"assigned_agent": agent}).is_success
    placeholder = c.put(path + "/readiness", json={"supporting_evidence": "TBD"}).json()
    assert not next(
        item["recorded"]
        for item in placeholder["items"]
        if item["label"] == "Supporting evidence"
    )
    partial = c.put(
        path + "/readiness", json={"error": "No error message was displayed."}
    ).json()
    assert not partial["ready"] and "Supporting evidence" in partial["summary"]
    results = {step: "Test observation for " + step for step in ticket["guide"]}
    assert c.patch(path + "/checklist", json={"results": results}).is_success
    assert (
        c.patch(path + "/checklist", json={"checks": CHECKS}).json()["results"]
        == results
    )
    evidence = {
        "error": "No error message displayed.",
        "reproduction": "Compared the two views for the same record.",
        "supporting_evidence": "Comparison recorded at 09:10 in this test.",
        "reason": "Difference persists after all recorded checks.",
    }
    ready = c.put(path + "/readiness", json=evidence).json()
    assert ready["ready"] and all(item["recorded"] for item in ready["items"])
    for part in (
        ticket_id,
        ticket["client_name"],
        *evidence.values(),
        *results.values(),
    ):
        assert part in ready["summary"]
    assert (
        c.post(path + "/analyse").json()["result"]["recommended_action"]
        == "Engineering Escalation Recommended"
    )
    refreshed = c.get(path).json()
    assert (
        refreshed["readiness"] == ready
        and refreshed["handoff_evidence"]["error"] == evidence["error"]
    )
    assert (
        refreshed["original"] == ticket["original"]
        and refreshed["status"] == ticket["status"]
    )
    assert (
        refreshed["eng_ticket_id"] == ticket["eng_ticket_id"]
        and refreshed["eng_handoffs"] == ticket["eng_handoffs"]
    )
    assert c.post(path + "/escalate").status_code == 410
    assert c.patch(path, json={"status": "Open - with Engineering"}).status_code == 409
    assert c.patch(path + "/checklist", json={"results": {}}).is_success
    assert not c.get(path).json()["readiness"]["ready"]
    before = c.get("/api/analytics/overview").json()
    assert c.post(
        path + "/resolve", json={"text": "Verified outcome for this isolated test."}
    ).is_success
    assert c.get(path).json()["status"] == "Closed"
    assert c.get("/api/analytics/overview").json() == before
    assert (
        c.patch(path, json={"status": "Open - with L1"}).json()["reopen_count"]
        == ticket["reopen_count"] + 1
    )
    with factory() as conn:
        assert conn.get(Ticket, ticket_id).original == ticket["original"]
        assert conn.scalar(select(func.count()).select_from(Audit)) > 0


def test_csv_dashboard(client):
    c, _ = client
    rows = import_csv.read_csv(import_csv.DATA_DIR / "rideops_support_tickets.csv")

    def compare(selected, metrics):
        sent = [r for r in selected if r["escalated_to_eng"] == "Yes"]
        returned = sum(r["eng_outcome"].endswith("returned to L1") for r in sent)
        reopened = sum(int(r["reopen_count"]) > 0 for r in selected)
        scores = [int(r["csat_score"]) for r in selected if r["csat_score"]]
        assert metrics["total"] == len(selected)
        assert metrics["client_count"] == len({r["client_id"] for r in selected})
        assert metrics["open"] == sum(r["status"] != "Closed" for r in selected)
        assert metrics["engineering_open"] == sum(
            r["status"] == "Open - with Engineering" for r in selected
        )
        assert metrics["escalated"] == len(sent) and metrics["returned"] == returned
        assert metrics["returned_rate"] == (
            round(100 * returned / len(sent), 1) if sent else None
        )
        assert metrics["escalation_rate"] == (
            round(100 * len(sent) / len(selected), 1) if selected else None
        )
        assert metrics["reopened"] == reopened
        assert metrics["reopen_rate"] == (
            round(100 * reopened / len(selected), 1) if selected else None
        )
        assert metrics["rated"] == len(scores)
        assert metrics["csat"] == (
            round(sum(scores) / len(scores), 2) if scores else None
        )

    report = c.get("/api/analytics/overview").json()
    compare(rows, report["kpis"])
    for category in report["categories"]:
        group = [r for r in rows if r["category"] == category["name"]]
        compare(group, category)
        compare(
            group,
            c.get(
                "/api/analytics/overview", params={"category": category["name"]}
            ).json()["kpis"],
        )
    for month in report["monthly"]:
        group = [r for r in rows if r["created_at"][:7] == month["date"][:7]]
        assert month["total"] == len(group) and month["escalated"] == sum(
            r["escalated_to_eng"] == "Yes" for r in group
        )
    compare([], c.get("/api/analytics/overview?category=missing").json()["kpis"])
    no_sent = next(
        r for r in rows if r["escalated_to_eng"] == "No" and not r["csat_score"]
    )
    day = no_sent["created_at"][:10]
    params = {
        "client": no_sent["client_name"],
        "category": no_sent["category"],
        "priority": no_sent["priority"],
        "start": day,
        "end": day,
    }
    selected = [
        r
        for r in rows
        if r["client_name"] == params["client"]
        and r["category"] == params["category"]
        and r["priority"] == params["priority"]
        and r["created_at"][:10] == day
    ]
    compare(selected, c.get("/api/analytics/overview", params=params).json()["kpis"])


def test_search_knowledge_and_validation(client):
    c, _ = client
    r = c.get("/api/tickets?limit=1").json()["items"][0]
    path = "/api/tickets/" + r["ticket_id"]
    fields = {
        "title": r["category"] + " guide",
        "category": r["category"],
        "issue": r["description"],
        "steps": "Document the observed outcome.",
        "resolution": "",
    }
    item = c.post("/api/knowledge", json=fields).json()
    assert (
        c.get(
            "/api/knowledge", params={"q": r["description"], "category": r["category"]}
        ).json()[0]["id"]
        == item["id"]
    )
    assert c.get(path).json()["articles"][0]["id"] == item["id"]
    assert c.put(
        "/api/knowledge/" + str(item["id"]),
        json={**fields, "resolution": "Reviewed resolution"},
    ).is_success
    assert c.delete("/api/knowledge/" + str(item["id"])).status_code == 204
    assert not c.get(path).json()["articles"]
    assert c.get("/api/tickets/missing").status_code == 404
    assert c.post(path + "/notes", json={"text": "  "}).status_code == 422
    assert c.patch(path, json={"assigned_agent": "Missing agent"}).status_code == 422
    assert (
        c.put(path + "/checklist", json={"checks": ["Unrecognised"]}).status_code == 422
    )
    assert c.get("/api/tickets?page=0").status_code == 422
    assert (
        c.get("/api/analytics/overview?start=2026-10-01&end=2026-07-01").status_code
        == 422
    )
    blank = c.get("/api/analytics/overview?category=invalid").json()
    assert blank["kpis"]["total"] == 0 and blank["kpis"]["csat"] is None
    params = {
        "category": r["category"],
        "client": r["client_name"],
        "priority": r["priority"],
        "start": r["created_at"][:10],
        "end": r["created_at"][:10],
    }
    n = c.get("/api/tickets", params=params).json()["total"]
    report = list(
        csv.DictReader(io.StringIO(c.get("/api/analytics/export", params=params).text))
    )
    assert int(report[0]["total"]) == n and n >= 1


def test_groq_failures_and_validation(client, monkeypatch):
    c, _ = client
    path = (
        "/api/tickets/"
        + c.get("/api/tickets?limit=1").json()["items"][0]["ticket_id"]
        + "/analyse"
    )
    valid = c.post(path).json()["result"]
    monkeypatch.setenv("GROQ_API_KEY", "test-only")
    request = httpx.Request("POST", "https://example.invalid")
    calls = []

    def fake(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        import json

        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(valid)}}]},
            request=request,
        )

    monkeypatch.setattr(ai.httpx, "post", fake)
    assert c.post(path).json()["source"] == "Groq" and len(calls) == 2
    monkeypatch.setattr(
        ai.httpx,
        "post",
        lambda *a, **k: httpx.Response(200, json={"choices": []}, request=request),
    )
    assert c.post(path).json()["source"] == "Predefined rules"

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(ai.httpx, "post", timeout)
    assert c.post(path).json()["source"] == "Predefined rules"


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_hosted_postgres_url(monkeypatch, scheme):
    monkeypatch.setenv(
        "DATABASE_URL", f"{scheme}://demo:p%40ss@db.test:5544/tickets?sslmode=require"
    )
    url = db.database_url()
    assert url.drivername == "postgresql+psycopg" and url.password == "p@ss"
    assert (url.host, url.port, url.database) == ("db.test", 5544, "tickets")
    assert url.query["sslmode"] == "require"
