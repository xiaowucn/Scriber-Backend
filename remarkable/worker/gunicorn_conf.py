"""gunicorn WSGI server configuration."""

# pylint: skip-file
import platform
from os import environ

from remarkable.config import get_config

wsgi_app = "remarkable.server:create_app"
bind = "0.0.0.0:" + str((get_config("web.http_port") or get_config("web.domain").split(":")[-1]))
worker_class = "remarkable.worker.pai_uvicorn.PAIUvicornWorker"
workers = environ.get("SCRIBER_WEB_NUM") or 2
reuse_port = platform.system() == "Linux"
graceful_timeout = 90
timeout = 300
