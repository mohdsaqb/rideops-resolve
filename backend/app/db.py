import os
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)


def database_url():
    configured = os.getenv("DATABASE_URL")
    if configured:
        url = make_url(configured)
        if url.drivername in ("postgres", "postgresql"):
            return url.set(drivername="postgresql+psycopg")
        return url
    return URL.create(
        "postgresql+psycopg",
        username="rideops",
        password=os.getenv("POSTGRES_PASSWORD", "rideops"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database="rideops",
    )


engine = create_engine(database_url(), pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"
    name: Mapped[str] = mapped_column(String(100), primary_key=True)


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    category: Mapped[str] = mapped_column(String(160), index=True)
    client: Mapped[str] = mapped_column(String(160), index=True)
    # Immutable copy of every original CSV value, including empty fields.
    original: Mapped[dict] = mapped_column(JSON)


class State(Base):
    __tablename__ = "ticket_state"
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    agent: Mapped[str] = mapped_column(ForeignKey("agents.name"))
    status: Mapped[str] = mapped_column(String(60), index=True)
    changes: Mapped[dict] = mapped_column(JSON, default=dict)


class Event(Base):
    __tablename__ = "ticket_updates"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    text: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(default=now)


class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    handoff: Mapped[dict] = mapped_column(JSON)
    override_reason: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(30))
    checks: Mapped[list] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(default=now)


class Checklist(Base):
    __tablename__ = "checklist_results"
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    checks: Mapped[list] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)


class Article(Base):
    __tablename__ = "knowledge_articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(160), index=True)
    issue: Mapped[str] = mapped_column(Text)
    steps: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(default=False)
    verification: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)


class Recommendation(Base):
    __tablename__ = "ai_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"), index=True)
    source: Mapped[str] = mapped_column(String(40))
    result: Mapped[dict] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(default=now)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(160), index=True)
    at: Mapped[datetime] = mapped_column(default=now)


def session():
    with Session() as db:
        yield db


class DemoRoster(Base):
    __tablename__ = "demo_rosters"
    ticket_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    booking_cutoff: Mapped[str | None] = mapped_column(String(8))
    roster_cutoff: Mapped[str] = mapped_column(String(8))
