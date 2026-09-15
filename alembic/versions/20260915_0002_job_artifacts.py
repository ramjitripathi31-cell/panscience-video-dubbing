"""add demo pipeline persistence"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260915_0002"
down_revision = "20260915_0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'cancel_requested'")
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'cancelled'")
    uuid = postgresql.UUID(as_uuid=True)
    for table, columns in {
        "transcript_segments": [sa.Column("id", uuid, primary_key=True), sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("speaker_id", sa.String(100), nullable=False), sa.Column("start_time", sa.Float, nullable=False), sa.Column("end_time", sa.Float, nullable=False), sa.Column("source_text", sa.Text, nullable=False)],
        "translations": [sa.Column("id", uuid, primary_key=True), sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("language", sa.String(16), nullable=False), sa.Column("segment_id", uuid, sa.ForeignKey("transcript_segments.id", ondelete="CASCADE"), nullable=False), sa.Column("translated_text", sa.Text, nullable=False)],
        "artifacts": [sa.Column("id", uuid, primary_key=True), sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("language", sa.String(16)), sa.Column("artifact_type", sa.String(32), nullable=False), sa.Column("path", sa.Text, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)],
        "job_events": [sa.Column("id", uuid, primary_key=True), sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("message", sa.Text), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)],
    }.items():
        op.create_table(table, *columns)
        op.create_index(f"ix_{table}_job_id", table, ["job_id"])

def downgrade() -> None:
    for table in ("job_events", "artifacts", "translations", "transcript_segments"):
        op.drop_index(f"ix_{table}_job_id", table_name=table); op.drop_table(table)
