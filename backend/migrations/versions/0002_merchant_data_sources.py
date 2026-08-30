"""Merchant Razorpay credentials and ingestion tracking."""
from alembic import op
import sqlalchemy as sa

revision="0002_merchant_data_sources"
down_revision="0001_initial"
branch_labels=None
depends_on=None

def upgrade():
    inspector=sa.inspect(op.get_bind())
    existing_columns={x["name"] for x in inspector.get_columns("razorpay_connections")}
    for name,column in [
        ("key_id_encrypted",sa.Text()),("key_secret_encrypted",sa.Text()),
        ("webhook_secret_encrypted",sa.Text()),("webhook_token",sa.String(64)),
        ("last_sync_at",sa.DateTime()),("sync_status",sa.String(24)),
        ("sync_error",sa.Text()),("imported_orders",sa.Integer()),("imported_payments",sa.Integer()),
    ]:
        if name not in existing_columns:op.add_column("razorpay_connections",sa.Column(name,column,nullable=True))
    existing_indexes={x["name"] for x in inspector.get_indexes("razorpay_connections")}
    if "ix_razorpay_connections_webhook_token" not in existing_indexes:op.create_index("ix_razorpay_connections_webhook_token","razorpay_connections",["webhook_token"],unique=True)
    if "data_ingestion_runs" not in inspector.get_table_names():op.create_table("data_ingestion_runs",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("merchant_id",sa.String(36),sa.ForeignKey("merchants.id",ondelete="CASCADE"),nullable=False),
        sa.Column("source",sa.String(32),nullable=False),sa.Column("idempotency_key",sa.String(128),nullable=False),
        sa.Column("status",sa.String(24),nullable=False),sa.Column("counts",sa.JSON(),nullable=False),
        sa.Column("error",sa.Text()),sa.Column("started_at",sa.DateTime(),nullable=False),sa.Column("completed_at",sa.DateTime()),
        sa.UniqueConstraint("merchant_id","source","idempotency_key"))
    ingestion_indexes={x["name"] for x in sa.inspect(op.get_bind()).get_indexes("data_ingestion_runs")}
    for name,columns in [("ix_data_ingestion_runs_merchant_id",["merchant_id"]),("ix_data_ingestion_runs_source",["source"]),("ix_data_ingestion_runs_status",["status"]),("ix_data_ingestion_runs_started_at",["started_at"])]:
        if name not in ingestion_indexes:op.create_index(name,"data_ingestion_runs",columns)

def downgrade():
    op.drop_table("data_ingestion_runs")
    op.drop_index("ix_razorpay_connections_webhook_token",table_name="razorpay_connections")
    for name in ["imported_payments","imported_orders","sync_error","sync_status","last_sync_at","webhook_token","webhook_secret_encrypted","key_secret_encrypted","key_id_encrypted"]:
        op.drop_column("razorpay_connections",name)
