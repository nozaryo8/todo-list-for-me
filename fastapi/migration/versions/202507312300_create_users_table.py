"""create users table

Revision ID: 7278da130e29
Revises: 
Create Date: 2025-07-31 23:00:09.054180+09:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7278da130e29'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('login_id', sa.String(50), nullable=False),
        sa.Column('password', sa.Text(), nullable=False),
    )

def downgrade():
    op.drop_table('users')
