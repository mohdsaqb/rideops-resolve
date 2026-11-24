from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "agents",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_subject"), "audit_logs", ["subject"], unique=False
    )
    op.create_table(
        "knowledge_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=False),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("steps", sa.Text(), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_articles_category"),
        "knowledge_articles",
        ["category"],
        unique=False,
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=False),
        sa.Column("client", sa.String(length=160), nullable=False),
        sa.Column("original", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_category"), "tickets", ["category"], unique=False)
    op.create_index(op.f("ix_tickets_client"), "tickets", ["client"], unique=False)
    op.create_index(
        op.f("ix_tickets_created_at"), "tickets", ["created_at"], unique=False
    )
    op.create_table(
        "ai_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_recommendations_ticket_id"),
        "ai_recommendations",
        ["ticket_id"],
        unique=False,
    )
    op.create_table(
        "checklist_results",
        sa.Column("ticket_id", sa.String(length=40), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
        ),
        sa.PrimaryKeyConstraint("ticket_id"),
    )
    op.create_table(
        "escalations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.String(length=40), nullable=False),
        sa.Column("handoff", sa.JSON(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_escalations_ticket_id"), "escalations", ["ticket_id"], unique=False
    )
    op.create_table(
        "ticket_state",
        sa.Column("ticket_id", sa.String(length=40), nullable=False),
        sa.Column("agent", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent"],
            ["agents.name"],
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
        ),
        sa.PrimaryKeyConstraint("ticket_id"),
    )
    op.create_index(
        op.f("ix_ticket_state_status"), "ticket_state", ["status"], unique=False
    )
    op.create_table(
        "ticket_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=60), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_updates_ticket_id"),
        "ticket_updates",
        ["ticket_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_ticket_updates_ticket_id"), table_name="ticket_updates")
    op.drop_table("ticket_updates")
    op.drop_index(op.f("ix_ticket_state_status"), table_name="ticket_state")
    op.drop_table("ticket_state")
    op.drop_index(op.f("ix_escalations_ticket_id"), table_name="escalations")
    op.drop_table("escalations")
    op.drop_table("checklist_results")
    op.drop_index(
        op.f("ix_ai_recommendations_ticket_id"), table_name="ai_recommendations"
    )
    op.drop_table("ai_recommendations")
    op.drop_index(op.f("ix_tickets_created_at"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_client"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_category"), table_name="tickets")
    op.drop_table("tickets")
    op.drop_index(
        op.f("ix_knowledge_articles_category"), table_name="knowledge_articles"
    )
    op.drop_table("knowledge_articles")
    op.drop_index(op.f("ix_audit_logs_subject"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("agents")
