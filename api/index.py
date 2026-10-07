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
    Vercel rewrites all traffic to /api/index.
    This middleware ensures PATH_INFO is cleanly normalized:
    - /api/index or /api/index.py -> /
    - /api/index/login -> /login
    - Preserves all real routes so Flask matches correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
        
        # Check if original path is stored in headers
        matched = environ.get("HTTP_X_MATCHED_PATH")
        if matched and matched not in ("/api/index", "/api/index.py"):
            environ["PATH_INFO"] = matched
        elif path in ("/api/index", "/api/index.py", "/api", "/api/"):
            environ["PATH_INFO"] = "/"
        elif path.startswith("/api/index/"):
            environ["PATH_INFO"] = path[10:] or "/"
        elif path.startswith("/api/index.py/"):
            environ["PATH_INFO"] = path[13:] or "/"

        return self.wsgi_app(environ, start_response)

# Expose WSGI application wrapped with Vercel path fix
handler = VercelPathFixMiddleware(app)
app = handler

if __name__ == "__main__":
    app.run()
