"""Manage imported files and their editable payment records."""

from alembic import op
import sqlalchemy as sa

revision = "0005_import_file_management"
down_revision = "0004_remove_simulation_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {x["name"] for x in inspector.get_columns("data_ingestion_runs")}
    with op.batch_alter_table("data_ingestion_runs") as batch:
        if "filename" not in columns:
            batch.add_column(sa.Column("filename", sa.String(180), nullable=True))
        if "records" not in columns:
            batch.add_column(sa.Column("records", sa.JSON(), nullable=True))
        if "removed_at" not in columns:
            batch.add_column(sa.Column("removed_at", sa.DateTime(), nullable=True))
    indexes = {x["name"] for x in sa.inspect(op.get_bind()).get_indexes("data_ingestion_runs")}
    if "ix_data_ingestion_runs_removed_at" not in indexes:
        op.create_index("ix_data_ingestion_runs_removed_at", "data_ingestion_runs", ["removed_at"])


def downgrade() -> None:
    indexes = {x["name"] for x in sa.inspect(op.get_bind()).get_indexes("data_ingestion_runs")}
    if "ix_data_ingestion_runs_removed_at" in indexes:
        op.drop_index("ix_data_ingestion_runs_removed_at", table_name="data_ingestion_runs")
    with op.batch_alter_table("data_ingestion_runs") as batch:
        batch.drop_column("removed_at")
        batch.drop_column("records")
        batch.drop_column("filename")
