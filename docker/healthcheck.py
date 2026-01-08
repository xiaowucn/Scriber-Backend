# -*- coding:utf-8 -*-
import fcntl
import os
import pathlib
import traceback

import requests
import sys
if os.getenv("PSYCOPG2_GAUSS", "").lower() == "true":
    sys.path.insert(0, "/usr/lib/paoding/dist-packages")
    
from remarkable.common.util import loop_wrapper
from remarkable.config import get_config
from remarkable.db import pw_db

lock_file = pathlib.Path("/tmp/healthcheck.lock")


def check_supervisor():
    try:
        from xmlrpc.client import ServerProxy

        import supervisor.xmlrpc

        proxy = ServerProxy(
            "http://127.0.0.1",
            transport=supervisor.xmlrpc.SupervisorTransport(None, None, serverurl="unix:///dev/shm/supervisor.sock"),
        )

        for status in proxy.supervisor.getAllProcessInfo():
            assert status["statename"] == "RUNNING"
    except:
        print(traceback.print_exc())
        os.sys.exit(1)


def check_url_status(url, status_codes=(200,)):
    try:
        request_code = requests.get(url, headers={"User-agent": "Chrome"}, timeout=0.5).status_code
        assert request_code in status_codes
    except:
        print(f"url: {url} status code {request_code}, not in {status_codes}.")
        os.sys.exit(2)


def check_remote_port(address, port):
    import socket

    with socket.socket() as sk:
        try:
            sk.settimeout(10)
            sk.connect((address, int(port)))
        except socket.error:
            print(f"address: {address}, port: {port} connect refused.")
            os.sys.exit(3)


@loop_wrapper
async def query_pg_version():
    return await pw_db.scalar("SELECT version_num FROM alembic_version")


def check_pg():
    try:
        assert query_pg_version()
    except:
        print("postgresql not connected.")
        os.sys.exit(4)


def check_redis():
    redis_address = get_config("redis.host")
    redis_port = get_config("redis.port")
    check_remote_port(redis_address, redis_port)


def check_nginx_and_api():
    check_url_status("http://127.0.0.1:8000/index.html")
    check_url_status("http://127.0.0.1:8000/api/v1/test", (200, 401))


def check_pdfinsight_web():
    endpoint = get_config("app.auth.pdfinsight.url")

    import re

    reg = "http://([\w|\.|\-]*)(?::(\d*))?"
    result = re.match(reg, endpoint)
    remote_address = result.groups()[0]
    remote_port = result.groups()[1] if result.groups()[0] else 80
    check_remote_port(remote_address, remote_port)


def check():
    check_supervisor()

    if os.environ.get("SCRIBER_CONFIG_SZSE_SERVICE") == "True":
        check_remote_port("127.0.0.1", 50051)
    else:
        check_pg()
        check_redis()
        check_nginx_and_api()
        check_pdfinsight_web()


if __name__ == "__main__":
    lock_file.exists() or lock_file.touch()
    with open(lock_file, "r") as lock_f:
        try:
            fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            check()
            fcntl.flock(lock_f, fcntl.LOCK_UN)
        except BlockingIOError:
            print("healthcheck is already running")
            os.sys.exit(2)
