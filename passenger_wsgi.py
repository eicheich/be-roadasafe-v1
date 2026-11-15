import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from a2wsgi import ASGIMiddleware
from app.main import app

application = ASGIMiddleware(app)
