"""Optional account display names; preserve existing accounts."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('accounts',sa.Column('display_name',sa.String(80),nullable=False,server_default=''))
def downgrade():
    raise RuntimeError('Preserve account profile data; downgrade requires a reviewed migration')
