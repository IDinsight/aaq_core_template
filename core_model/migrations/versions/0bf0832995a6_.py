"""empty message

Revision ID: 0bf0832995a6
Revises: c86ead81ee4f
Create Date: 2023-02-08 13:11:13.816198

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0bf0832995a6"
down_revision = "c86ead81ee4f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "faqmatches", sa.Column("faq_contexts", sa.ARRAY(sa.String()), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("faqmatches", "faq_contexts")
    # ### end Alembic commands ###
