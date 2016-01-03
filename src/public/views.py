"""
Logic for dashboard related routes
"""
import os
from flask import Blueprint, render_template,send_from_directory
from flask_login import current_user

blueprint = Blueprint('public', __name__)

@blueprint.route('/favicon.ico', methods=['GET'])
def favicon():
    return send_from_directory(os.path.join(blueprint.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@blueprint.route('/', methods=['GET'])
def index():
    if not current_user:
        user=[]
    else:
        user=current_user
    return render_template('public/index.tmpl',user=user)
