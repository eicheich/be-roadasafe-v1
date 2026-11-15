import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from a2wsgi import ASGIMiddleware
from app.main import app

_asgi_wrapper = None
_wrapper_pid = None


def application(environ, start_response):
    """
    Lazy fork-safe WSGI wrapper for cPanel Passenger / LiteSpeed LSWSGI.
    Initializes ASGIMiddleware inside the worker process after fork()
    so the asyncio event loop thread is alive in the worker.
    """
    global _asgi_wrapper, _wrapper_pid
    current_pid = os.getpid()
    if _asgi_wrapper is None or _wrapper_pid != current_pid:
        _asgi_wrapper = ASGIMiddleware(app, wait_time=10.0)
        _wrapper_pid = current_pid
    return _asgi_wrapper(environ, start_response)
