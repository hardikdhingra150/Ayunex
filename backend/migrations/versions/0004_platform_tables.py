"""Version the platform tables previously created at application startup."""
from alembic import op
import sqlalchemy as sa

revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind();existing=sa.inspect(bind).get_table_names()
    if 'platform_consents' not in existing:
        op.create_table('platform_consents',sa.Column('id',sa.String(36),primary_key=True),
            sa.Column('tenant',sa.String(160),nullable=False),sa.Column('subject',sa.String(160),nullable=False),
            sa.Column('purpose',sa.String(80),nullable=False),sa.Column('notice_version',sa.String(40),nullable=False),
            sa.Column('status',sa.String(20),nullable=False),sa.Column('granted_at',sa.String(40),nullable=False),
            sa.Column('withdrawn_at',sa.String(40)),sa.Column('metadata_json',sa.Text()))
        op.create_index('ix_platform_consents_subject','platform_consents',['tenant','subject','purpose'])
    if 'platform_audit_ledger' not in existing:
        op.create_table('platform_audit_ledger',sa.Column('id',sa.String(36),primary_key=True),
            sa.Column('sequence',sa.Integer(),nullable=False),sa.Column('tenant',sa.String(160),nullable=False),
            sa.Column('actor',sa.String(160),nullable=False),sa.Column('action',sa.String(80),nullable=False),
            sa.Column('timestamp',sa.String(40),nullable=False),sa.Column('prev_hash',sa.String(64),nullable=False),
            sa.Column('entry_hash',sa.String(64),nullable=False),sa.Column('payload_json',sa.Text()))
        op.create_index('ix_platform_audit_seq','platform_audit_ledger',['sequence'])
    indices={i['name'] for i in sa.inspect(bind).get_indexes('platform_audit_ledger')}
    if 'ux_platform_audit_sequence' not in indices:
        op.create_index('ux_platform_audit_sequence','platform_audit_ledger',['sequence'],unique=True)
    for table in ('platform_consents','platform_audit_ledger'):
        column=next(c for c in sa.inspect(bind).get_columns(table) if c['name']=='id')
        if column['nullable']:
            with op.batch_alter_table(table) as batch:
                batch.alter_column('id',existing_type=sa.String(36),nullable=False)

def downgrade():
    # Retain user consent/audit history; schema rollback must not delete it.
    op.drop_index('ux_platform_audit_sequence',table_name='platform_audit_ledger')
