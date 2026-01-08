"""Test helper functions for the Remarkable project."""

import http
import logging
import os
import urllib.parse
from io import BytesIO
from zipfile import ZipFile

import requests

from remarkable.config import get_config


def sync_file_for_test(args: tuple) -> dict | None:
    """Sync file from remote server for testing purposes.

    This is a test helper function that downloads and extracts file data
    from a remote Remarkable instance for local testing.

    Args:
        args: Tuple of (file_id, mold, pdf_cache, local_path, host, model_version)

    Returns:
        Dictionary containing file metadata, or None if sync failed
    """
    import json

    from remarkable.common.storage import localstorage

    file_id, mold, pdf_cache, local_path, host, model_version = args
    parsed_host = urllib.parse.urlparse(host)
    try:
        if local_path and os.path.isfile(local_path):
            zip_file = ZipFile(open(local_path, "rb"))
        else:
            url = (
                f"{parsed_host.scheme}://{parsed_host.netloc}{parsed_host.path}/api/v1/plugins/debug/file/{file_id}/export/{int(pdf_cache)}?key="
                f"u-never-know&mold={mold or 0}&model_version={int(model_version)}"
            )
            logging.info(url)
            rsp = requests.get(url, timeout=60)
            if rsp.status_code != http.HTTPStatus.OK:
                logging.error(f"{file_id} download failed, status code: {rsp.status_code}, content: {rsp.content}")
                return None
            zip_file = ZipFile(BytesIO(rsp.content), "r")
        add_prefix = get_config("client.add_time_hierarchy", False)
        meta = None
        for filename in zip_file.namelist():
            if filename == "meta.json":
                data = zip_file.read(filename)
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                meta = json.loads(data)
            elif filename.startswith(localstorage.cache_root):
                if pdf_cache:
                    localstorage.write_file(filename, zip_file.read(filename))
            else:
                if add_prefix:
                    filepath = filename
                else:
                    filepath = os.path.join(filename[:2], filename[2:])
                localstorage.write_file(filepath, zip_file.read(filename))
    except Exception as exp:
        logging.error(exp)
        meta = []
    return meta

