"""create jobs table"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260915_0001"
down_revision = None
branch_labels = None
depends_on = None

job_status = postgresql.ENUM("pending", "running", "succeeded", "failed", name="job_status", create_type=False)


def upgrade() -> None:
    job_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("current_stage", sa.String(length=100), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("target_languages", postgresql.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count"),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_table("jobs")
    job_status.drop(op.get_bind(), checkfirst=True)
