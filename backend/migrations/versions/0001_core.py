"""Initial Module B schema. Immutable revision: 0001."""
from alembic import op
import sqlalchemy as sa

revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('cases',sa.Column('id',sa.String(36),primary_key=True),sa.Column('tenant',sa.String(160),nullable=False),sa.Column('owner',sa.String(160),nullable=False),sa.Column('title',sa.String(160),nullable=False),sa.Column('status',sa.String(40),nullable=False),sa.Column('query_kind',sa.String(32),nullable=False),sa.Column('jurisdiction',sa.JSON(),nullable=False),sa.Column('as_of',sa.String(10),nullable=False),sa.Column('passport',sa.JSON(),nullable=False),sa.Column('passport_version',sa.Integer(),nullable=False),sa.Column('consent',sa.JSON(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    for field in ['tenant','owner']:op.create_index('ix_cases_'+field,'cases',[field])
    op.create_table('product_passport_versions',sa.Column('id',sa.String(36),primary_key=True),sa.Column('case_id',sa.String(36),sa.ForeignKey('cases.id',ondelete='CASCADE'),nullable=False),sa.Column('version',sa.Integer(),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('case_id','version'))
    op.create_index('ix_product_passport_versions_case_id','product_passport_versions',['case_id'])
    op.create_table('case_artifacts',sa.Column('id',sa.String(36),primary_key=True),sa.Column('case_id',sa.String(36),sa.ForeignKey('cases.id',ondelete='CASCADE'),nullable=False),sa.Column('kind',sa.String(32),nullable=False),sa.Column('context_hash',sa.String(64),nullable=False),sa.Column('idempotency_key',sa.String(128)),sa.Column('request_hash',sa.String(64)),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('case_id','kind','idempotency_key'))
    for field in ['case_id','kind']:op.create_index('ix_case_artifacts_'+field,'case_artifacts',[field])
    op.create_table('domain_event_outbox',sa.Column('id',sa.String(36),primary_key=True),sa.Column('case_id',sa.String(36),sa.ForeignKey('cases.id',ondelete='CASCADE'),nullable=False),sa.Column('tenant',sa.String(160),nullable=False),sa.Column('actor',sa.String(160),nullable=False),sa.Column('action',sa.String(80),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    for field in ['case_id','tenant']:op.create_index('ix_domain_event_outbox_'+field,'domain_event_outbox',[field])

def downgrade():
    for table in ['domain_event_outbox','case_artifacts','product_passport_versions','cases']:op.drop_table(table)
