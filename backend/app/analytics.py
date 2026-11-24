from collections import Counter, defaultdict
from datetime import datetime, timedelta

import numpy as np

RETURN_OUTCOMES = {
    "Insufficient info - returned to L1",
    "Config issue - returned to L1",
}


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def mean(values):
    return round(float(np.mean(values)), 2) if values else None


def stats(rows):
    n = len(rows)
    closed = sum(r["status"] == "Closed" for r in rows)
    escalated = sum(r["escalated_to_eng"] == "Yes" for r in rows)
    returned = sum(
        r["escalated_to_eng"] == "Yes" and r["eng_outcome"] in RETURN_OUTCOMES
        for r in rows
    )
    reopened = sum(r["reopen_count"] > 0 for r in rows)
    hours = [
        (
            datetime.fromisoformat(r["final_closed_at"])
            - datetime.fromisoformat(r["created_at"])
        ).total_seconds()
        / 3600
        for r in rows
        if r["final_closed_at"] and r["status"] == "Closed"
    ]
    scores = [r["csat_score"] for r in rows if r["csat_score"] is not None]
    return {
        "total": n,
        "returned": returned,
        "returned_rate": pct(returned, escalated),
        "client_count": len({r["client_id"] for r in rows if r["client_id"]}),
        "engineering_open": sum(r["status"] == "Open - with Engineering" for r in rows),
        "open": n - closed,
        "resolved": closed,
        "escalated": escalated,
        "reopened": reopened,
        "escalation_rate": pct(escalated, n),
        "reopen_rate": pct(reopened, n),
        "csat": mean(scores),
        "rated": len(scores),
        "resolution_hours": mean(hours),
    }


def groups(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[r[key]].append(r)
    return out


def distribution(rows, key):
    return [
        {"name": name, "value": n}
        for name, n in Counter(r[key] for r in rows if r[key]).most_common()
    ]


def trends(rows, weekly):
    buckets = defaultdict(list)
    for r in rows:
        day = datetime.fromisoformat(r["created_at"]).date()
        start = day - timedelta(days=day.weekday()) if weekly else day.replace(day=1)
        buckets[start].append(r)
    if not buckets:
        return []
    cursor, last = min(buckets), max(buckets)
    points = []
    while cursor <= last:
        batch = buckets[cursor]
        points.append(
            {
                "date": cursor.isoformat(),
                "total": len(batch),
                "escalated": sum(r["escalated_to_eng"] == "Yes" for r in batch),
                "resolved": sum(r["status"] == "Closed" for r in batch),
            }
        )
        cursor = (
            cursor + timedelta(days=7)
            if weekly
            else (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        )
    return points


def overview(rows, snapshot_date):
    k = stats(rows)
    cats = [
        dict(name=name, **stats(batch))
        for name, batch in groups(rows, "category").items()
    ]
    cats.sort(key=lambda c: -c["total"])
    # Average percentile rank across the five dimensions, ignoring unavailable measures.
    for c in cats:
        ranks = []
        for metric in (
            "total",
            "escalation_rate",
            "reopen_rate",
            "csat",
            "resolution_hours",
        ):
            if c[metric] is None:
                continue
            values = [d[metric] for d in cats if d[metric] is not None]
            ranks.append(
                sum(
                    (v >= c[metric] if metric == "csat" else v <= c[metric])
                    for v in values
                )
                / len(values)
            )
        c["impact"] = round(100 * sum(ranks) / len(ranks))
    insights = []

    def add(title, body):
        insights.append({"title": title, "body": body})

    if cats:
        focus = [
            c
            for c in cats
            if c["name"]
            in ("Roster / booking not syncing", "Live tracking / GPS incorrect")
        ]
        focus_sent = sum(c["escalated"] for c in focus)
        if focus_sent:
            add(
                "Roster and GPS handoffs",
                f"These categories account for {focus_sent} of {k['escalated']} escalated tickets in this selection. "
                f"{sum(c['returned'] for c in focus)} received a return-to-L1 outcome.",
            )
        c = cats[0]
        add(
            "Highest ticket volume",
            f"{c['name']} accounts for {c['total']} of {k['total']} tickets.",
        )
        for field, title, desc in [
            ("escalation_rate", "Engineering demand", "went to engineering"),
            ("reopen_rate", "Repeated investigations", "were reopened"),
        ]:
            c = max(cats, key=lambda x: x[field])
            add(
                title, f"{c[field]}% of the {c['total']} tickets in {c['name']} {desc}."
            )
        rated = [c for c in cats if c["rated"]]
        if rated:
            c = min(rated, key=lambda x: x["csat"])
            add(
                "Lowest customer satisfaction",
                f"{c['name']} averaged {c['csat']}/5 from {c['rated']} ratings.",
            )
        patterns = distribution(rows, "description")
        if patterns and patterns[0]["value"] > 1:
            pattern = patterns[0]
            add(
                "Recurring issue",
                f"{pattern['value']} tickets share the description “{pattern['name']}”.",
            )
    oldest = sorted(
        (r for r in rows if r["status"] != "Closed"), key=lambda r: r["created_at"]
    )
    if oldest:
        r = oldest[0]
        add(
            "Oldest unresolved ticket",
            f"{r['ticket_id']} · {r['description']}. Created {r['created_at']} IST.",
        )
    ageing = Counter()
    for r in oldest:
        days = (snapshot_date - datetime.fromisoformat(r["created_at"]).date()).days
        ageing[
            "0–7 days" if days <= 7 else "8–30 days" if days <= 30 else "31+ days"
        ] += 1
    return {
        "oldest_open": oldest[:5],
        "kpis": k,
        "categories": cats,
        "weekly": trends(rows, True),
        "monthly": trends(rows, False),
        "priorities": distribution(rows, "priority"),
        "statuses": distribution(rows, "status"),
        "clients": distribution(rows, "client_name"),
        "outcomes": distribution(rows, "eng_outcome"),
        "ageing": [{"name": k, "value": v} for k, v in ageing.items()],
        "insights": insights,
        "baseline": k,
        "range": [
            min((r["created_at"][:10] for r in rows), default=None),
            max((r["created_at"][:10] for r in rows), default=None),
        ],
    }
