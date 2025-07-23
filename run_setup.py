from omcrm import create_app, db
from omcrm.tasks.models import Task, TaskComment
from omcrm.users.models import User

app = create_app()

with app.app_context():
    # Just create the tables without trying to do migrations
    # This is a simple way to handle it for SQLite
    db.create_all()
    
    print("Database updated successfully!") 