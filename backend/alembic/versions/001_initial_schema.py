"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "traders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.Text()),
        sa.Column("email", sa.Text(), index=True),
        sa.Column("phone", sa.Text()),
        sa.Column("address", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("country", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("product_tags", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("priority_flag", sa.Boolean(), server_default="false"),
        sa.Column("email_valid", sa.Boolean(), nullable=True),
        sa.Column(
            "email_status",
            sa.Enum("pending", "sent", "bounced", "replied", name="emailstatus"),
            server_default="pending",
        ),
        sa.Column("approved", sa.Boolean(), server_default="false"),
        sa.Column("scraped_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text()),
        sa.Column("status", sa.Text(), server_default="created"),
        sa.Column("target_regions", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("total_traders", sa.Text(), server_default="0"),
        sa.Column("sent_count", sa.Text(), server_default="0"),
        sa.Column("bounced_count", sa.Text(), server_default="0"),
        sa.Column("replied_count", sa.Text(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "email_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trader_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("traders.id")),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "sent", "bounced", "replied", name="emailstatus"),
            server_default="pending",
        ),
        sa.Column("sendgrid_message_id", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("email_logs")
    op.drop_table("campaigns")
    op.drop_table("traders")
    op.execute("DROP TYPE IF EXISTS emailstatus")
