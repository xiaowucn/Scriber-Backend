import base64
import json
from urllib.parse import urlencode

from remarkable import config
from remarkable.common.util import generate_timestamp
from remarkable.security.authtoken import _generate_token
from remarkable.security.crypto_util import aes_encrypt


def create_cgs_params(url: str, data: dict, encode=True):
    app_id = config.get_config("cgs.auth.app_id")
    secret_key = config.get_config("cgs.auth.secret_key")
    zero_padding = config.get_config("cgs.auth.zero_padding", True)

    result = aes_encrypt(json.dumps(data).encode("utf-8"), key=secret_key, fill=zero_padding)
    params = {
        "_u": base64.b64encode(result).decode("utf-8"),
        "_timestamp": generate_timestamp(),
    }
    params["_token"] = _generate_token(
        url=url, appid=app_id, secret=secret_key, extra_params=params, timestamp=params["_timestamp"]
    )

    if encode:
        return urlencode(params)

    return params
