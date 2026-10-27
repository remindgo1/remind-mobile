"""Create Phase 1 accounts, profiles, relationships, and linking codes."""

from alembic import op
import sqlalchemy as sa

revision = "0001_phase1_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("firebase_uid", sa.String(length=128), primary_key=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('caregiver', 'patient')", name="ck_accounts_role"),
    )
    op.create_table(
        "patient_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("created_by_uid", sa.String(length=128), sa.ForeignKey("accounts.firebase_uid"), nullable=False),
        sa.Column("patient_uid", sa.String(length=128), sa.ForeignKey("accounts.firebase_uid"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "care_relationships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("caregiver_uid", sa.String(length=128), sa.ForeignKey("accounts.firebase_uid"), nullable=False),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("can_manage_profile", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("caregiver_uid", "patient_id", name="uq_care_relationship"),
    )
    op.create_table(
        "link_codes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("patient_profiles.id"), nullable=False),
        sa.Column("created_by_uid", sa.String(length=128), sa.ForeignKey("accounts.firebase_uid"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_uid", sa.String(length=128), sa.ForeignKey("accounts.firebase_uid"), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("link_codes")
    op.drop_table("care_relationships")
    op.drop_table("patient_profiles")
    op.drop_table("accounts")
