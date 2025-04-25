"""
Migration script to add credit_balance to the Lead model
"""
from flask import Flask
from omcrm import db, create_app
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add credit_balance column to Lead table
    op.add_column('lead', sa.Column('credit_balance', sa.Float(), nullable=False, server_default='0.0'))
    
    # Set default values for credit_balance
    op.execute("UPDATE lead SET credit_balance = 0.0 WHERE credit_balance IS NULL")

def downgrade():
    # Remove credit_balance column
    op.drop_column('lead', 'credit_balance')

def run_migration():
    app = create_app()
    with app.app_context():
        upgrade()
        print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration() 
