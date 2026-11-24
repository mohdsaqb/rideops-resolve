import csv
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, text

from .db import Agent, Session, State, Ticket

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def read_csv(path):
    try:
        import pandas as pd
    except ImportError:
        with path.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))
    return pd.read_csv(path, dtype=str, keep_default_na=False).to_dict("records")


def run():
    dictionary = read_csv(DATA_DIR / "rideops_data_dictionary.csv")
    rows = read_csv(DATA_DIR / "rideops_support_tickets.csv")
    required = {
        field.strip() for entry in dictionary for field in entry["column"].split("/")
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Ticket file does not match the data dictionary")
    with Session.begin() as db:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(727665)"))
        ids = set(db.scalars(select(Ticket.id)))
        agents = set(db.scalars(select(Agent.name)))
        names = {r["assigned_agent"] for r in rows}
        db.add_all(Agent(name=name) for name in names - agents)
        pending = [r for r in rows if r["ticket_id"] not in ids]
        db.add_all(
            Ticket(
                id=r["ticket_id"],
                original=r,
                created_at=datetime.fromisoformat(r["created_at"]),
                category=r["category"],
                client=r["client_name"],
            )
            for r in pending
        )
        db.flush()
        db.add_all(
            State(
                ticket_id=r["ticket_id"],
                agent=r["assigned_agent"],
                status=r["status"],
                changes={},
            )
            for r in pending
        )
    return len(pending)


if __name__ == "__main__":
    print(f"Imported {run()} tickets")
