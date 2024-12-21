from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'lolrahhali'
    app.config['SESSION_TYPE'] = 'filesystem'  
    app.config['SESSION_COOKIE_SECURE'] = True  
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    Session(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    return app
