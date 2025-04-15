import os

# Basisconfiguratie voor de applicatie
class Config:
    # Database configuratie
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///carrentals.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Flask-configuratie
    SECRET_KEY = os.environ.get("SESSION_SECRET", "ontwikkelsleutel-vervangen-in-productie")
    
    # Upload-configuratie
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads/documents')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB maximale bestandsgrootte
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'}
    
    @classmethod
    def init_app(cls, app):
        # Base configuration init
        pass
    
    # SendGrid-configuratie voor e-mails (optioneel)
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    DEFAULT_MAIL_SENDER = os.environ.get("DEFAULT_MAIL_SENDER", "noreply@autoverhuur.nl")

# Ontwikkelconfiguratie
class DevelopmentConfig(Config):
    DEBUG = True
    
# Testconfiguratie
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    
# Productieconfiguratie
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
    # Zorg ervoor dat er altijd een geheime sleutel is ingesteld
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Hier kunt u productie-specifieke instellingen toevoegen
        if not os.environ.get("SESSION_SECRET"):
            raise RuntimeError(
                "SESSION_SECRET environment variable is not set. "
                "This is required for secure sessions in production."
            )

# Configuratie-omgeving bepalen
config_env = os.environ.get("FLASK_ENV", "development").lower()

# De juiste configuratie selecteren op basis van de omgevingsvariabele
if config_env == "production":
    app_config = ProductionConfig
elif config_env == "testing":
    app_config = TestingConfig
else:
    app_config = DevelopmentConfig