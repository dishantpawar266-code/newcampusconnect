import os
import sys

# Ensure root project directory is on sys.path so app and its modules are found
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import app

class VercelPathFixMiddleware:
    """
    Vercel CLI 62+ rewrites request paths to destination (/api/index.py).
    This middleware restores the original requested path from x-matched-path
    so Flask routes (/, /login, /dashboard, etc.) resolve properly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get("HTTP_X_MATCHED_PATH")
        if matched and environ.get("PATH_INFO") in ("/api/index.py", "/api/index"):
            environ["PATH_INFO"] = matched
        return self.wsgi_app(environ, start_response)

# Expose WSGI application wrapped with Vercel path fix
handler = VercelPathFixMiddleware(app)
app = handler

if __name__ == "__main__":
    app.run()
