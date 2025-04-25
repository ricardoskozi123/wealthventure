from flask import Blueprint

tasks = Blueprint('tasks', __name__)

from omcrm.tasks import routes 
