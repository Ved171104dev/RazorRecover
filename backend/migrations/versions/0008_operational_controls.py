"""Add provider notification, maker-checker and operational controls.

Revision ID: 0008_operational_controls
Revises: 0007_recovery_proof_reliability
"""
from alembic import op
import sqlalchemy as sa

revision="0008_operational_controls"
down_revision="0007_recovery_proof_reliability"
branch_labels=None
depends_on=None

def _columns(table):
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}
def _indexes(table):
    return {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table)}
def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())

def upgrade():
    if "contact_opt_out" not in _columns("customers"):op.add_column("customers",sa.Column("contact_opt_out",sa.Boolean(),nullable=False,server_default=sa.false()))
    if "ix_customers_contact_opt_out" not in _indexes("customers"):op.create_index("ix_customers_contact_opt_out","customers",["contact_opt_out"])
    action_columns=_columns("recovery_actions")
    if any(name not in action_columns for name in ["created_by_user_id","reconciliation_attempts","next_reconcile_at"]):
        with op.batch_alter_table("recovery_actions") as batch:
            if "created_by_user_id" not in action_columns:
                batch.add_column(sa.Column("created_by_user_id",sa.String(36),nullable=True));batch.create_foreign_key("fk_recovery_actions_created_by","users",["created_by_user_id"],["id"])
            if "reconciliation_attempts" not in action_columns:batch.add_column(sa.Column("reconciliation_attempts",sa.Integer(),nullable=False,server_default="0"))
            if "next_reconcile_at" not in action_columns:batch.add_column(sa.Column("next_reconcile_at",sa.DateTime(),nullable=True))
    if "ix_recovery_actions_created_by_user_id" not in _indexes("recovery_actions"):op.create_index("ix_recovery_actions_created_by_user_id","recovery_actions",["created_by_user_id"])
    if "ix_recovery_actions_next_reconcile_at" not in _indexes("recovery_actions"):op.create_index("ix_recovery_actions_next_reconcile_at","recovery_actions",["next_reconcile_at"])
    if "requested_by_user_id" not in _columns("approvals"):
        with op.batch_alter_table("approvals") as batch:
            batch.add_column(sa.Column("requested_by_user_id",sa.String(36),nullable=True));batch.create_foreign_key("fk_approvals_requested_by","users",["requested_by_user_id"],["id"])
    webhook_columns=_columns("webhook_events")
    if "replay_count" not in webhook_columns:op.add_column("webhook_events",sa.Column("replay_count",sa.Integer(),nullable=False,server_default="0"))
    if "last_replayed_at" not in webhook_columns:op.add_column("webhook_events",sa.Column("last_replayed_at",sa.DateTime(),nullable=True))
    policy_columns=_columns("merchant_policies")
    for name,column,default in [("maker_checker_enabled",sa.Boolean(),sa.false()),("daily_contact_limit",sa.Integer(),"2"),("quiet_hours_start_utc",sa.Integer(),"20"),("quiet_hours_end_utc",sa.Integer(),"8"),("max_model_brier_score",sa.Float(),"0.25"),("incident_auto_pause_enabled",sa.Boolean(),sa.true())]:
        if name not in policy_columns:op.add_column("merchant_policies",sa.Column(name,column,nullable=False,server_default=default))
    if "recovery_contact_events" not in _tables():op.create_table(
        "recovery_contact_events",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("merchant_id",sa.String(36),sa.ForeignKey("merchants.id",ondelete="CASCADE"),nullable=False),
        sa.Column("recovery_action_id",sa.String(36),sa.ForeignKey("recovery_actions.id",ondelete="CASCADE"),nullable=False),
        sa.Column("customer_id",sa.String(36),sa.ForeignKey("customers.id"),nullable=False),
        sa.Column("medium",sa.String(16),nullable=False),
        sa.Column("attempt_number",sa.Integer(),nullable=False),
        sa.Column("status",sa.String(24),nullable=False),
        sa.Column("provider_response",sa.JSON(),nullable=False),
        sa.Column("requested_by_user_id",sa.String(36),sa.ForeignKey("users.id"),nullable=True),
        sa.Column("created_at",sa.DateTime(),nullable=False),
        sa.UniqueConstraint("recovery_action_id","medium","attempt_number"),
    )
    existing_contact_indexes=_indexes("recovery_contact_events")
    for column in ["merchant_id","recovery_action_id","customer_id","medium","status","created_at"]:
        if f"ix_recovery_contact_events_{column}" not in existing_contact_indexes:op.create_index(f"ix_recovery_contact_events_{column}","recovery_contact_events",[column])

def downgrade():
    op.drop_table("recovery_contact_events")
    for name in ["incident_auto_pause_enabled","max_model_brier_score","quiet_hours_end_utc","quiet_hours_start_utc","daily_contact_limit","maker_checker_enabled"]:
        op.drop_column("merchant_policies",name)
    op.drop_column("webhook_events","last_replayed_at")
    op.drop_column("webhook_events","replay_count")
    with op.batch_alter_table("approvals") as batch:
        batch.drop_constraint("fk_approvals_requested_by",type_="foreignkey")
        batch.drop_column("requested_by_user_id")
    op.drop_index("ix_recovery_actions_next_reconcile_at",table_name="recovery_actions")
    op.drop_index("ix_recovery_actions_created_by_user_id",table_name="recovery_actions")
    with op.batch_alter_table("recovery_actions") as batch:
        batch.drop_constraint("fk_recovery_actions_created_by",type_="foreignkey")
        batch.drop_column("next_reconcile_at")
        batch.drop_column("reconciliation_attempts")
        batch.drop_column("created_by_user_id")
    op.drop_index("ix_customers_contact_opt_out",table_name="customers")
    op.drop_column("customers","contact_opt_out")
