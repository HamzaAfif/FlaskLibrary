from flask import Blueprint, render_template

views = Blueprint('views', __name__)

@views.route('/')
def home():
    user = 'hamza'
    return render_template("home.html", user=user)

