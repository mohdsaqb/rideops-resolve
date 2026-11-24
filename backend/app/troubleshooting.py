from .schemas import Handoff, Readiness, ReadinessItem

GUIDES = {
    "Roster / booking not syncing": [
        "Verify roster status",
        "Check employee mapping",
        "Check shift assignment",
        "Verify synchronization status",
    ],
    "Live tracking / GPS incorrect": [
        "Check the last GPS update",
        "Verify driver connectivity",
        "Confirm vehicle identification",
        "Determine whether one or multiple vehicles are affected",
    ],
    "Report export failing": [
        "Verify date filters",
        "Check report permissions",
        "Verify export status",
    ],
    "OTP / boarding issue": [
        "Verify employee mobile details",
        "Check OTP generation",
        "Confirm trip status",
    ],
    "Billing / invoice discrepancy": [
        "Verify invoice period",
        "Check trip counts",
        "Compare billing records",
    ],
}
HYPOTHESES = {
    "Roster / booking not syncing": [
        "A mapping or shift mismatch could prevent the booking from appearing."
    ],
    "Live tracking / GPS incorrect": [
        "A delayed GPS update or interrupted driver connectivity could explain a stale location."
    ],
    "Report export failing": [
        "The selected filters, report permissions, or export job state may affect the export."
    ],
    "OTP / boarding issue": [
        "The mobile number on file or the trip state may affect OTP generation."
    ],
    "Billing / invoice discrepancy": [
        "The billing period or trip count may differ between records."
    ],
}
GENERIC = [
    "Confirm the affected record and time window",
    "Document expected and observed behaviour",
    "Record evidence and the scope of impact",
]


GUIDANCE = {
    "Roster / booking not syncing": {
        "checks": [
            "Compare the reported booking with the roster for the same date and shift.",
            "Record the affected employee identifier and the roster entry it maps to.",
            "Compare the booking’s shift with the shift displayed to the dispatcher.",
            "Record the last visible sync time and whether the mismatch is still present.",
        ],
        "resolve": "Resolve at L1 when the booking and roster agree for the affected shift and the requester confirms the correct entry is visible.",
        "engineering": "Request engineering review if the same booking still differs after mapping and shift checks. Include the identifiers, timestamps and both observed values.",
    },
    "Live tracking / GPS incorrect": {
        "checks": [
            "Record the last location timestamp and the time the discrepancy was observed.",
            "Ask the driver or dispatcher to confirm connectivity at that time.",
            "Match the vehicle and trip identifiers on both views.",
            "Compare another vehicle or trip and record how many are affected.",
        ],
        "resolve": "Resolve at L1 when the correct vehicle shows a current position and the requester confirms tracking is working.",
        "engineering": "Request engineering review if the same vehicle and trip still show stale or conflicting positions after the connectivity check. Include times, scope and the evidence.",
    },
}


def guidance(ticket):
    return GUIDANCE.get(
        ticket["category"],
        {
            "checks": [],
            "resolve": "Resolve at L1 when you can verify the expected behaviour on the affected record and confirm the outcome with the requester.",
            "engineering": "Request engineering review if the issue persists after the applicable checks. Record the observed difference, impact and evidence.",
        },
    )


def documented(value):
    return bool(
        value
        and value.strip(" .…-").casefold()
        not in {
            "",
            "unknown",
            "n/a",
            "tbd",
            "pending",
            "not recorded",
            "not checked",
            "not available",
        }
    )


def readiness(ticket, results):
    evidence = ticket.get("handoff_evidence", {})
    steps = GUIDES.get(ticket["category"], GENERIC)
    outstanding = [step for step in steps if not documented(results.get(step))]
    fields = [
        ("Issue description", ticket["description"], "Record the reported behaviour."),
        ("Affected client", ticket["client_name"], "Identify the affected client."),
        (
            "Error information",
            evidence.get("error"),
            "Record the exact error or the symptom if no error appeared.",
        ),
        (
            "Reproduction steps",
            evidence.get("reproduction"),
            "Record how to observe the issue, or explain why it cannot be reproduced.",
        ),
        (
            "Troubleshooting attempted",
            None if outstanding else "All proposed checks have observations.",
            "Still to document: " + ", ".join(outstanding),
        ),
        (
            "Supporting evidence",
            evidence.get("supporting_evidence"),
            "Record a reference or the compared values and timestamps.",
        ),
        (
            "Reason for engineering review",
            evidence.get("reason"),
            "Explain what still needs investigation.",
        ),
    ]
    items = [
        ReadinessItem(
            label=label,
            recorded=documented(value),
            detail=value if documented(value) else hint,
        )
        for label, value, hint in fields
    ]
    missing = [item.label for item in items if not item.recorded]
    recorded = "\n".join(
        f"- {step}: {results[step]}" for step in steps if results.get(step)
    )
    summary = "\n".join(
        [
            f"Engineering handoff draft · {ticket['ticket_id']}",
            f"Client: {ticket['client_name']} | Category: {ticket['category']} | Priority: {ticket['priority']}",
            f"Reported issue: {ticket['description']}",
            f"Expected behaviour: {evidence.get('expected') or 'Unconfirmed'}",
            f"Error or observed symptom: {evidence.get('error') or 'Not recorded'}",
            f"Reproduction: {evidence.get('reproduction') or 'Not recorded'}",
            "Troubleshooting and results:",
            recorded or "No observations recorded.",
            f"Evidence: {evidence.get('supporting_evidence') or 'Not recorded'}",
            f"Reason for review: {evidence.get('reason') or 'Not recorded'}",
            "Missing information: "
            + (", ".join(missing) or "No checklist gaps. Agent review required."),
        ]
    )
    return Readiness(items=items, ready=not missing, summary=summary)


def prepare_handoff(ticket, results, review=None):
    steps = GUIDES.get(ticket["category"], GENERIC)
    missing = [step for step in steps if not documented(results.get(step))]
    review = review or readiness(ticket, results)
    missing.extend(
        item.label
        for item in review.items
        if not item.recorded and item.label != "Troubleshooting attempted"
    )
    evidence = ticket.get("handoff_evidence", {})
    records = "\n".join(f"{step}: {value}" for step, value in results.items())
    if len(records) > 8000:
        records = (
            records[:7900]
            + "\n[Excerpt. Full results are saved in the ticket checklist.]"
        )
    issue = ticket["description"]
    return Handoff(
        issue_summary=issue,
        actual_behaviour=evidence.get("error") or issue,
        expected_behaviour=evidence.get("expected") or "Confirm with the customer.",
        troubleshooting_completed="\n".join(results) or "No troubleshooting recorded.",
        results=records or "No results recorded.",
        missing_information="\n".join(missing)
        or "Confirm any additional evidence with the agent.",
        reason_for_escalation=evidence.get("reason")
        or "Agent review required. Document why L1 cannot resolve the issue.",
    )
