import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import app_config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app(config=app_config):
    """Application factory voor flexibele configuratie en testen."""
    # Create the Flask app
    app = Flask(__name__)
    
    # Configuratie laden
    app.config.from_object(config)
    app.secret_key = app.config['SECRET_KEY']
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https
    
    # Zorg dat uploads map bestaat
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configure Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # specify the login view endpoint in the auth blueprint
    login_manager.login_message = 'Log in om deze pagina te bekijken.'
    login_manager.login_message_category = 'info'
    
    # Initialize database
    db.init_app(app)
    
    return app

# Create the app instance
app = create_app()

# Initialize database tables
with app.app_context():
    # Import models to create the tables
    import models  # noqa: F401
    
    db.create_all()
