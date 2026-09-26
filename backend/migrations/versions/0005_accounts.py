"""Verified accounts and revocable browser sessions."""
from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('accounts',sa.Column('id',sa.String(36),primary_key=True),sa.Column('email',sa.String(254),nullable=False,unique=True),sa.Column('password_hash',sa.String(256),nullable=False),sa.Column('tenant',sa.String(36),nullable=False),sa.Column('verified',sa.Boolean(),nullable=False),sa.Column('role',sa.String(24),nullable=False),sa.Column('failures',sa.Integer(),nullable=False),sa.Column('locked_until',sa.Integer(),nullable=False))
    for name in ('account_sessions','account_actions'):
        columns=[sa.Column('digest',sa.String(64),primary_key=True),sa.Column('account_id',sa.String(36),sa.ForeignKey('accounts.id',ondelete='CASCADE'),nullable=False),sa.Column('expires',sa.Integer(),nullable=False)]
        if name=='account_actions':columns.append(sa.Column('purpose',sa.String(16),nullable=False))
        op.create_table(name,*columns)
        op.create_index('ix_'+name+'_account_id',name,['account_id'])

def downgrade():
    raise RuntimeError('Account data must not be deleted by an automatic downgrade')
