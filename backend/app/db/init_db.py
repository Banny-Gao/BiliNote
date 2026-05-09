from sqlalchemy import inspect, text

from app.db.models.models import Model
from app.db.models.providers import Provider
from app.db.models.video_tasks import VideoTask
from app.db.engine import get_engine, Base


def _ensure_column(engine, table_name: str, column_def: str):
    """Add column to existing table if it doesn't exist (SQLite-safe)."""
    inspector = inspect(engine)
    if table_name in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        col_name = column_def.split()[0]
        if col_name not in existing:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}"))
                conn.commit()


def init_db():
    engine = get_engine()

    Base.metadata.create_all(bind=engine)

    # ── schema migrations for existing tables ──
    _ensure_column(engine, "models", "vision_supported INTEGER DEFAULT 1")
