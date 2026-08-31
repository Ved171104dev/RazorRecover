"""Disable simulation for merchant policies by default."""
from alembic import op
import sqlalchemy as sa

revision="0003_real_data_only"
down_revision="0002_merchant_data_sources"
branch_labels=None
depends_on=None

def upgrade():
    columns={x["name"] for x in sa.inspect(op.get_bind()).get_columns("merchant_policies")}
    if "simulation_mode" in columns:
        op.execute(sa.text("UPDATE merchant_policies SET simulation_mode = false"))
        with op.batch_alter_table("merchant_policies") as batch:
            batch.alter_column("simulation_mode",existing_type=sa.Boolean(),server_default=sa.false(),nullable=False)

def downgrade():
    columns={x["name"] for x in sa.inspect(op.get_bind()).get_columns("merchant_policies")}
    if "simulation_mode" in columns:
        with op.batch_alter_table("merchant_policies") as batch:
            batch.alter_column("simulation_mode",existing_type=sa.Boolean(),server_default=sa.true(),nullable=False)
