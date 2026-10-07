import os
import sys

# Ensure root project directory is on sys.path so app and its modules are found
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import app

import urllib.parse

class VercelPathFixMiddleware:
    """
    Vercel rewrites all traffic to /api/index?__vercel_path=/$1.
    This middleware extracts the real target path and restores it into PATH_INFO
    so all Flask routes (/, /login, /register, /dashboard, etc.) work seamlessly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        
        # 1. Primary path resolver: extract __vercel_path injected by vercel.json rewrite
        if "__vercel_path=" in query_string:
            qs = urllib.parse.parse_qs(query_string, keep_blank_values=True)
            if "__vercel_path" in qs and qs["__vercel_path"]:
                target_path = qs["__vercel_path"][0].strip()
                # Clean up query string so Flask doesn't see internal parameter
                remaining = [
                    p for p in query_string.split("&")
                    if p and not p.startswith("__vercel_path=")
                ]
                environ["QUERY_STRING"] = "&".join(remaining)
                if not target_path.startswith("/"):
                    target_path = "/" + target_path
                environ["PATH_INFO"] = target_path or "/"
                return self.wsgi_app(environ, start_response)

        # 2. Secondary fallback: check HTTP_X_MATCHED_PATH
        matched = environ.get("HTTP_X_MATCHED_PATH")
        if matched and matched not in ("/api/index", "/api/index.py"):
            environ["PATH_INFO"] = matched
            return self.wsgi_app(environ, start_response)

        # 3. Tertiary fallback: clean up direct invocations
        path = environ.get("PATH_INFO", "") or "/"
        if path in ("/api/index", "/api/index.py", "/api", "/api/"):
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
