"""Add causal assignment, shadow mode, and recovery delivery state."""

from alembic import op
import sqlalchemy as sa

revision = "0007_recovery_proof_reliability"
down_revision = "0006_regulatory_guardrails"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    with op.batch_alter_table("merchant_policies") as batch:
        if "shadow_mode" not in _columns("merchant_policies"):
            batch.add_column(sa.Column("shadow_mode", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "ix_merchant_policies_shadow_mode" not in _indexes("merchant_policies"):
        op.create_index("ix_merchant_policies_shadow_mode", "merchant_policies", ["shadow_mode"])

    with op.batch_alter_table("experiments") as batch:
        if "experiment_type" not in _columns("experiments"):
            batch.add_column(sa.Column("experiment_type", sa.String(32), nullable=False, server_default="observational"))
    if "ix_experiments_experiment_type" not in _indexes("experiments"):
        op.create_index("ix_experiments_experiment_type", "experiments", ["experiment_type"])

    with op.batch_alter_table("recovery_actions") as batch:
        action_columns = _columns("recovery_actions")
        if "delivery_status" not in action_columns:
            batch.add_column(sa.Column("delivery_status", sa.String(32), nullable=False, server_default="not_started"))
        if "delivery_channel" not in action_columns:
            batch.add_column(sa.Column("delivery_channel", sa.String(32), nullable=True))
    if "ix_recovery_actions_delivery_status" not in _indexes("recovery_actions"):
        op.create_index("ix_recovery_actions_delivery_status", "recovery_actions", ["delivery_status"])

    with op.batch_alter_table("experiment_results") as batch:
        result_columns = _columns("experiment_results")
        if "risk_event_id" not in result_columns:
            batch.add_column(sa.Column("risk_event_id", sa.String(36), nullable=True))
        if "assignment_group" not in result_columns:
            batch.add_column(sa.Column("assignment_group", sa.String(24), nullable=False, server_default="observed"))
    if "ix_experiment_results_risk_event_id" not in _indexes("experiment_results"):
        op.create_index("ix_experiment_results_risk_event_id", "experiment_results", ["risk_event_id"])
    if "ix_experiment_results_assignment_group" not in _indexes("experiment_results"):
        op.create_index("ix_experiment_results_assignment_group", "experiment_results", ["assignment_group"])


def downgrade() -> None:
    op.drop_index("ix_experiment_results_assignment_group", table_name="experiment_results")
    op.drop_index("ix_experiment_results_risk_event_id", table_name="experiment_results")
    with op.batch_alter_table("experiment_results") as batch:
        batch.drop_column("assignment_group")
        batch.drop_column("risk_event_id")
    op.drop_index("ix_recovery_actions_delivery_status", table_name="recovery_actions")
    with op.batch_alter_table("recovery_actions") as batch:
        batch.drop_column("delivery_channel")
        batch.drop_column("delivery_status")
    op.drop_index("ix_experiments_experiment_type", table_name="experiments")
    with op.batch_alter_table("experiments") as batch:
        batch.drop_column("experiment_type")
    op.drop_index("ix_merchant_policies_shadow_mode", table_name="merchant_policies")
    with op.batch_alter_table("merchant_policies") as batch:
        batch.drop_column("shadow_mode")
