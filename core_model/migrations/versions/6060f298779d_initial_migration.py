"""Initial migration.

Revision ID: 6060f298779d
Revises:
Create Date: 2022-10-31 23:04:59.733503

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6060f298779d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "faqmatches",
        "faq_tags",
        existing_type=postgresql.ARRAY(sa.TEXT()),
        nullable=True,
    )
    op.alter_column(
        "faqmatches",
        "faq_thresholds",
        existing_type=postgresql.ARRAY(sa.REAL()),
        nullable=True,
    )
    op.alter_column(
        "faqmatches",
        "faq_weight",
        existing_type=sa.INTEGER(),
        nullable=False,
        existing_server_default=sa.text("1"),
    )
    op.alter_column(
        "inbounds", "inbound_secret_key", existing_type=sa.TEXT(), nullable=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "inbounds", "inbound_secret_key", existing_type=sa.TEXT(), nullable=True
    )
    op.alter_column(
        "faqmatches",
        "faq_weight",
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text("1"),
    )
    op.alter_column(
        "faqmatches",
        "faq_thresholds",
        existing_type=postgresql.ARRAY(sa.REAL()),
        nullable=False,
    )
    op.alter_column(
        "faqmatches",
        "faq_tags",
        existing_type=postgresql.ARRAY(sa.TEXT()),
        nullable=False,
    )
    # ### end Alembic commands ###
