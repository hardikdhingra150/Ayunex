"""Versioned official corpus and immutable review trail."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('source_documents',sa.Column('id',sa.String(36),primary_key=True),sa.Column('source_key',sa.String(120),nullable=False),sa.Column('sha256',sa.String(64),nullable=False),sa.Column('title',sa.String(500),nullable=False),sa.Column('authority',sa.String(160),nullable=False),sa.Column('url',sa.Text(),nullable=False),sa.Column('domain',sa.String(80),nullable=False),sa.Column('country',sa.String(2),nullable=False),sa.Column('active',sa.Boolean(),nullable=False),sa.Column('metadata_json',sa.JSON(),nullable=False),sa.Column('retrieved_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('source_key','sha256'))
    op.create_index('ix_source_documents_source_key','source_documents',['source_key'])
    op.create_table('source_passages',sa.Column('id',sa.String(36),primary_key=True),sa.Column('document_id',sa.String(36),sa.ForeignKey('source_documents.id',ondelete='CASCADE'),nullable=False),sa.Column('page',sa.Integer(),nullable=False),sa.Column('text',sa.Text(),nullable=False),sa.Column('sha256',sa.String(64),nullable=False),sa.Column('review',sa.JSON(),nullable=False))
    op.create_index('ix_source_passages_document_id','source_passages',['document_id'])
    op.create_table('corpus_review_events',sa.Column('id',sa.String(36),primary_key=True),sa.Column('passage_id',sa.String(36),sa.ForeignKey('source_passages.id',ondelete='CASCADE'),nullable=False),sa.Column('actor',sa.String(160),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_corpus_review_events_passage_id','corpus_review_events',['passage_id'])

def downgrade():
    for table in ['corpus_review_events','source_passages','source_documents']:op.drop_table(table)
