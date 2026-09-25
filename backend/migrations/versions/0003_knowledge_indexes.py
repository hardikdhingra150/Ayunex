"""Immutable parse revisions, optimistic review writes, and embedding storage."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('source_passages',sa.Column('active',sa.Boolean(),nullable=False,server_default=sa.true()))
    op.add_column('source_passages',sa.Column('extraction',sa.JSON(),nullable=False,server_default='{}'))
    op.add_column('source_passages',sa.Column('review_revision',sa.Integer(),nullable=False,server_default='0'))
    op.create_table('passage_embeddings',
        sa.Column('passage_id',sa.String(36),sa.ForeignKey('source_passages.id',ondelete='CASCADE'),primary_key=True),
        sa.Column('model',sa.String(160),primary_key=True),sa.Column('text_sha256',sa.String(64),nullable=False),
        sa.Column('vector',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table('passage_embeddings')
    op.drop_column('source_passages','review_revision')
    op.drop_column('source_passages','extraction')
    op.drop_column('source_passages','active')
