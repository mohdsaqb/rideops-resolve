from alembic import context
from sqlalchemy import text
from app.db import engine, Base

with engine.begin() as connection:
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(727664)"))
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
