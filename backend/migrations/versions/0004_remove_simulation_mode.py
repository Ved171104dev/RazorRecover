"""Remove runtime simulation mode.

Revision ID: 0004_remove_simulation_mode
Revises: 0003_real_data_only
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_remove_simulation_mode"
down_revision = "0003_real_data_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE razorpay_connections SET mode = 'not_connected' WHERE mode = 'demo'"))
    op.execute(sa.text("UPDATE recovery_actions SET execution_mode = 'legacy_test_record' WHERE execution_mode = 'simulated'"))
    op.execute(sa.text("UPDATE orders SET data_source = 'test_fixture' WHERE data_source = 'seeded_demo'"))
    op.execute(sa.text("UPDATE payments SET data_source = 'test_fixture' WHERE data_source = 'seeded_demo'"))
    columns={x["name"] for x in sa.inspect(op.get_bind()).get_columns("merchant_policies")}
    if "simulation_mode" in columns:
        with op.batch_alter_table("merchant_policies") as batch:
            batch.drop_column("simulation_mode")


def downgrade() -> None:
    columns={x["name"] for x in sa.inspect(op.get_bind()).get_columns("merchant_policies")}
    if "simulation_mode" not in columns:
        with op.batch_alter_table("merchant_policies") as batch:
            batch.add_column(sa.Column("simulation_mode", sa.Boolean(), nullable=False, server_default=sa.false()))
