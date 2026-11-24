"""Preserve legacy guides as drafts and install the reviewed demonstration procedure."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    op.add_column(
        "knowledge_articles",
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "knowledge_articles",
        sa.Column("verification", sa.Text(), nullable=False, server_default=""),
    )
    demo = op.create_table(
        "demo_rosters",
        sa.Column("ticket_id", sa.String(40), primary_key=True),
        sa.Column("booking_cutoff", sa.String(8)),
        sa.Column("roster_cutoff", sa.String(8), nullable=False),
    )
    op.bulk_insert(
        demo,
        [
            dict(ticket_id="SUP-11422", booking_cutoff="08:30", roster_cutoff="08:00"),
            dict(ticket_id="SUP-11438", booking_cutoff=None, roster_cutoff="08:00"),
        ],
    )
    op.execute("""INSERT INTO knowledge_articles
        (id,title,category,issue,steps,resolution,verification,approved,updated_at)
        VALUES (-1,'Refresh a demo roster cutoff','Roster / booking not syncing',
        'Booking cutoff changed but roster still uses old cutoff',
        'Compare the booking cutoff and roster cutoff for the same demo shift.',
        'Copy the confirmed booking cutoff to the local demo roster.',
        'Read the saved roster back and compare it with the booking cutoff. A missing booking cutoff requires L1 investigation.',
        TRUE,CURRENT_TIMESTAMP)""")


def downgrade():
    op.execute("DELETE FROM knowledge_articles WHERE id = -1")
    op.drop_table("demo_rosters")
    op.drop_column("knowledge_articles", "verification")
    op.drop_column("knowledge_articles", "approved")
