import os
import sys

# Ensure root project directory is on sys.path so app and its modules are found
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import app

# Expose WSGI application for Vercel Serverless Function
handler = app

if __name__ == "__main__":
    app.run()
