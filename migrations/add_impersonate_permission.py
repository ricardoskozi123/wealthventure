"""add impersonate permission

Revision ID: add_impersonate_permission
Create Date: 2025-04-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_impersonate_permission'
down_revision = None  # This will need to be updated to the correct previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Add can_impersonate column to resource table with a default value of False
    op.add_column('resource', sa.Column('can_impersonate', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Remove the can_impersonate column on downgrade
    op.drop_column('resource', 'can_impersonate') 