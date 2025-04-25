from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from omcrm.config import DevelopmentConfig, TestConfig, ProductionConfig
import os
from omcrm import create_app, db
from flask.cli import FlaskGroup, with_appcontext
import sys
import click
import secrets
from omcrm.leads.models import LeadSource

# Create app with app factory
app = create_app()

# But also provide a Flask instance for other commands
flask_app = Flask(__name__, instance_relative_config=True)

config_class = ProductionConfig()
if os.getenv('FLASK_ENV') == 'development':
    config_class = DevelopmentConfig()
elif os.getenv('FLASK_ENV') == 'production':
    config_class = ProductionConfig()
    # Ensure security in production
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = False
    # Enforce HTTPS if not behind a proxy
    if not os.getenv('BEHIND_PROXY'):
        app.config['PREFERRED_URL_SCHEME'] = 'https'
elif os.getenv('FLASK_ENV') == 'testing':
    config_class = TestConfig()

flask_app.config.from_object(config_class)

flask_db = SQLAlchemy(flask_app)
migrate = Migrate(flask_app, flask_db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


class TestUser(flask_db.Model):
    id = flask_db.Column(flask_db.Integer, primary_key=True)
    name = flask_db.Column(flask_db.String(128))


@app.cli.command('run')
def run():
    """Run the application with the development server."""
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug)


@app.cli.command('create-api-key')
@click.argument('source_id', type=int)
@with_appcontext
def create_api_key(source_id):
    """Create or update API key for a lead source by ID."""
    try:
        source = LeadSource.query.get(source_id)
        if not source:
            click.echo(f"Error: No lead source found with ID {source_id}")
            return
        
        # Generate new API key
        api_key = secrets.token_hex(32)
        source.api_key = api_key
        source.is_api_enabled = True
        
        db.session.commit()
        click.echo(f"API key created for source '{source.source_name}'")
        click.echo(f"API Key: {api_key}")
        click.echo("API access is now enabled for this source")
            
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error: {str(e)}")


@app.cli.command('list-sources')
@with_appcontext
def list_sources():
    """List all lead sources with their API keys."""
    try:
        sources = LeadSource.query.all()
        if not sources:
            click.echo("No lead sources found in the database")
            return
            
        click.echo("Available lead sources:")
        for source in sources:
            status = "Enabled" if source.is_api_enabled else "Disabled"
            api_key = source.api_key or "Not set"
            click.echo(f"ID: {source.id} | Name: {source.source_name} | API Status: {status}")
            if source.is_api_enabled and source.api_key:
                click.echo(f"API Key: {api_key}")
                if source.affiliate_id:
                    click.echo(f"Affiliate ID: {source.affiliate_id}")
            click.echo("-" * 50)
            
    except Exception as e:
        click.echo(f"Error: {str(e)}")


if __name__ == '__main__':
    manager.run()
