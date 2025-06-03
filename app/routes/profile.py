from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('profile', __name__, url_prefix='/profile')

@bp.route('/')
@login_required
def index():
    return render_template('profile/index.html', user=current_user) 