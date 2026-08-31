"""Add payment-type classification and persisted recovery circuit breaker."""

from alembic import op
import sqlalchemy as sa

revision = "0006_regulatory_guardrails"
down_revision = "0005_import_file_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    payment_columns = {item["name"] for item in inspector.get_columns("payments")}
    with op.batch_alter_table("payments") as batch:
        if "payment_type" not in payment_columns:
            batch.add_column(sa.Column("payment_type", sa.String(24), nullable=False, server_default="one_time"))
    payment_indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("payments")}
    if "ix_payments_payment_type" not in payment_indexes:
        op.create_index("ix_payments_payment_type", "payments", ["payment_type"])
    policy_columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("merchant_policies")}
    with op.batch_alter_table("merchant_policies") as batch:
        if "recovery_paused_until" not in policy_columns:
            batch.add_column(sa.Column("recovery_paused_until", sa.DateTime(), nullable=True))
        if "recovery_pause_reason" not in policy_columns:
            batch.add_column(sa.Column("recovery_pause_reason", sa.Text(), nullable=True))
    policy_indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("merchant_policies")}
    if "ix_merchant_policies_recovery_paused_until" not in policy_indexes:
        op.create_index("ix_merchant_policies_recovery_paused_until", "merchant_policies", ["recovery_paused_until"])


def downgrade() -> None:
    op.drop_index("ix_merchant_policies_recovery_paused_until", table_name="merchant_policies")
    with op.batch_alter_table("merchant_policies") as batch:
        batch.drop_column("recovery_pause_reason")
        batch.drop_column("recovery_paused_until")
    op.drop_index("ix_payments_payment_type", table_name="payments")
    with op.batch_alter_table("payments") as batch:
        batch.drop_column("payment_type")
