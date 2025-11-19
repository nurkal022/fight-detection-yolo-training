from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os

db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    # Get the base directory (parent of app directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    # Load base configuration
    try:
        from app.config import Config
        app.config.from_object(Config)
    except Exception:
        pass

    # Configurations
    app.config['SECRET_KEY'] = app.config.get('SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-secret-key-other-version'))
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///detection_system.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    app.config['UPLOAD_FOLDER'] = app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = app.config.get('MAX_CONTENT_LENGTH', 500 * 1024 * 1024)
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('app/static/events', exist_ok=True)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.detection import detection_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(detection_bp, url_prefix='/detection')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            # Tables might already exist, ignore the error
            pass
    
    return app


