import base64
import functools
import json

from remarkable import config
from remarkable.common.exceptions import CustomError
from remarkable.config import get_config
from remarkable.models.new_user import NewAdminUser, TokenUser
from remarkable.security.authtoken import _validate_url
from remarkable.security.crypto_util import aes_decrypt
from remarkable.session import encode_permission


class CgsTokenValidator:
    def auth_check(self, this):
        url = this.request.full_url()
        if "X-Original-Request-URI" in this.request.headers:
            url = this.request.headers["X-Original-Request-URI"]
        passed, msg = _validate_url(
            url, self.app_id, self.secret, self.token_expire, exclude_path=True, exclude_domain=True
        )
        if passed:
            return passed, msg
        return _validate_url(url, self.app_id, self.secret, self.token_expire, exclude_domain=True, exclude_path=False)

    def __call__(self, method):
        @functools.wraps(method)
        def wrapper(this, *args, **kwargs):
            self.app_id = config.get_config("cgs.auth.app_id")
            self.secret = config.get_config("cgs.auth.secret_key")
            self.token_expire = config.get_config("cgs.token_expire", 3600)

            if this.current_user:
                return method(this, *args, **kwargs)
            passed, msg = self.auth_check(this)
            if not passed:
                raise CustomError(msg=msg, resp_status_code=403)
            this.current_user = TokenUser
            return method(this, *args, **kwargs)

        return wrapper


def login_from_api():
    async def login(this):
        secret = config.get_config("cgs.auth.secret_key")
        user_string = this.get_argument("_u")
        if not user_string:
            return False
        zero_padding = config.get_config("cgs.auth.zero_padding", True)
        user_data = json.loads(
            aes_decrypt(base64.b64decode(user_string.encode("utf-8")), key=secret, strip=zero_padding)
        )
        ext_name = user_data["uname"]
        ext_id = user_data["uid"]
        ext_from = user_data["sys_code"]
        perms = [{"perm": perm} for perm in get_config("cgs.user_perms_from_api", ["browse", "remark", "inspect"])]
        user = await NewAdminUser.find_by_kwargs(ext_id=ext_id)
        if not user:
            user = await NewAdminUser.create(
                **{
                    "name": ext_name,
                    "permission": perms,
                    "ext_id": ext_id,
                    "password": "",
                    "salt": "",
                    "department": "",
                    "department_id": "",
                    "data": user_data,
                    "ext_from": ext_from,
                }
            )
        this.set_secure_cookie("sys_code", ext_from, httponly=True)
        this.session["uid"] = str(user.id)
        this.session["perm"] = encode_permission(perms)
        this.session["name"] = str(ext_name)
        this.session["ext_id"] = ext_id
        this.session_sync()
        return True

    def inner(func):
        @functools.wraps(func)
        async def wrapper(this, *args, **kwargs):
            await login(this)
            return await func(this, *args, **kwargs)

        return wrapper

    return inner
