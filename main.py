from app import app  # noqa: F401
import routes  # noqa: F401

# Import and register the auth blueprint
from auth import auth_bp, init_auth

# Register the auth blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Initialize the auth module
with app.app_context():
    init_auth()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
