import os
from omcrm import create_app

# Set the environment to development to use dev.db
os.environ['FLASK_ENV'] = 'development'

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
