"""
sort params of origin url -> revised origin url
_token = hash(revised_origin_url + _app_id + secret_key + _timestamp)
url = revised_origin_url with _timestamp=_&_token=_
"""

import hashlib
import logging
import re
import urllib.parse

from utensils.auth.token import encode_url as u_encode_url
from utensils.auth.token import encode_url_v2 as u_encode_url_v2
from utensils.auth.token import validate_token_url_v2

from remarkable import config
from remarkable.common.constants import TokenStatus
from remarkable.common.util import generate_timestamp

logger = logging.getLogger(__name__)


def lstrip_subpath(path: str, cut_subpath: bool = False):
    # NOTE: 只有trident是切掉subpath后计算的token
    # '/scriber/api/v1/user/unify-login' -> '/api/v1/user/unify-login'
    if path.endswith("user/unify-login") or cut_subpath:
        return re.sub(r".*?(/api/v\d+/.*)", r"\1", path)

    return path


def revise_url(url, extra_params=None, excludes=None, exclude_domain=False, exclude_path=False, cut_subpath=False):
    extra_params = extra_params or {}
    excludes = excludes or []
    url_ret = urllib.parse.urlparse(url)
    main_url = lstrip_subpath(url_ret.path, cut_subpath)
    if url_ret.netloc:
        main_url = f"{url_ret.scheme}://{url_ret.netloc}{main_url}"
    query = url_ret.query

    if exclude_path:
        main_url = ""
    elif exclude_domain:
        main_url = urllib.parse.urlsplit(main_url).path

    params = urllib.parse.parse_qs(query) if query else {}
    params.update(extra_params)
    keys = list(params.keys())
    keys.sort()
    params_strings = []
    for key in keys:
        if key in excludes:
            continue
        values = params[key]
        if isinstance(values, list):
            values.sort()
            params_strings.extend([urllib.parse.urlencode({key: value}) for value in values])
        else:
            params_strings.append(urllib.parse.urlencode({key: values}))
    return "{}?{}".format(main_url, "&".join(params_strings)) if params_strings else main_url


def _generate_token(
    url, appid, secret, extra_params=None, timestamp=None, exclude_domain=False, exclude_path=False, cut_subpath=None
):
    if cut_subpath is None:
        cut_subpath = config.get_config("web.cut_subpath_for_token")
    url = revise_url(
        url,
        extra_params=extra_params,
        excludes=["_token", "_timestamp"],
        exclude_domain=exclude_domain,
        exclude_path=exclude_path,
        cut_subpath=cut_subpath,
    )
    timestamp_now = timestamp or generate_timestamp()
    source = "{}#{}#{}#{}".format(url, appid, secret, timestamp_now)
    logger.info(f"{source=}")
    token = hashlib.md5(source.encode()).hexdigest()
    return token


def encode_url(url, app_id, secret_key, params=None, timestamp=None, exclude_domain=False, exclude_path=False):
    timestamp = timestamp or generate_timestamp()
    token = _generate_token(
        url, app_id, secret_key, params, timestamp, exclude_domain=exclude_domain, exclude_path=exclude_path
    )
    extra_params = {"_timestamp": timestamp, "_token": token}
    extra_params.update(params or {})
    url = revise_url(url, extra_params=extra_params, exclude_domain=False)
    return url


def _validate_url(url, app_id, secret, token_expire=3600, exclude_domain=False, exclude_path=False) -> tuple[bool, str]:
    query = urllib.parse.splitquery(url)[1]
    params = urllib.parse.parse_qs(query) if query else {}
    token = params.get("_token", [None])[0]
    timestamp = params.get("_timestamp", [None])[0]
    if not (token and timestamp):
        return False, TokenStatus.MISSED.value
    if generate_timestamp() - int(timestamp) > token_expire:
        return False, TokenStatus.EXPIRED.value
    real_token = _generate_token(
        url, app_id, secret, timestamp=timestamp, exclude_domain=exclude_domain, exclude_path=exclude_path
    )
    passed = real_token == token
    logger.info(f"url:{url}, app_id:{app_id}, secret:{secret}")
    logger.info(f"token:{token}, real_token:{real_token}, validate:{passed}")

    return passed, TokenStatus.PASSED.value if passed else TokenStatus.INVALID.value


def validate_url(url, app_id=None, secret=None, token_expire=3600, exclude_domain=False) -> tuple[bool, str]:
    app_id = app_id or config.get_config("app.app_id")
    secret = secret or config.get_config("app.secret_key")
    token_expire = config.get_config("app.token_expire") or token_expire
    passed, msg = _validate_url(url, app_id, secret, token_expire, exclude_domain=exclude_domain)
    if passed:
        return True, msg
    if exclude_domain:
        return validate_url(url, app_id, secret, token_expire)
    if validate_token_url_v2(url, app_id, secret, token_expire=token_expire):
        return True, TokenStatus.PASSED.value
    return False, msg


def encode_test_url(url, app_id=None, secret_key=None, exclude_domain=False):
    app_id = app_id or config.get_config("app.app_id")
    secret_key = secret_key or config.get_config("app.secret_key")
    return u_encode_url(url, app_id, secret_key, exclude_domain=exclude_domain)


def encode_test_url_v2(url, app_id=None, secret_key=None):
    app_id = app_id or config.get_config("app.app_id")
    secret_key = secret_key or config.get_config("app.secret_key")
    return u_encode_url_v2(url, app_id, secret_key)
