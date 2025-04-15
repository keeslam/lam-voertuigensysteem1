"""
WSGI entrypoint voor de applicatie.
Dit bestand kan worden gebruikt door WSGI servers zoals Gunicorn.
"""

from app import app as application

# Voor compatibiliteit met verschillende WSGI-servers
app = application

if __name__ == "__main__":
    application.run()