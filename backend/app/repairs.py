"""One reviewed, local-only repair. Neither article text nor model output is executable."""

from sqlalchemy import select

from .db import DemoRoster

ARTICLE_ID = -1
SCRIPT = "refresh-demo-cutoff-v1"
DESCRIPTION = "Booking cutoff changed but roster still uses old cutoff"


def matches(ticket):
    return (
        ticket["category"] == "Roster / booking not syncing"
        and ticket["description"] == DESCRIPTION
    )


def refresh_cutoff(db, ticket_id):
    record = db.scalar(
        select(DemoRoster).where(DemoRoster.ticket_id == ticket_id).with_for_update()
    )
    if not record or not record.booking_cutoff:
        return (
            False,
            "The demo booking has no confirmed cutoff. Collect the shift settings before retrying.",
        )
    record.roster_cutoff = record.booking_cutoff
    db.flush()
    db.refresh(record)
    verified = record.booking_cutoff == record.roster_cutoff
    if verified:
        return (
            True,
            f"Demo roster read back at {record.roster_cutoff}, matching the booking cutoff.",
        )
    return (
        False,
        "The saved demo roster differs from the booking cutoff. Investigate the shift.",
    )
