from uvicorn_worker import UvicornWorker


class PAIUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {"loop": "uvloop", "http": "httptools", "lifespan": "on", "factory": True}
