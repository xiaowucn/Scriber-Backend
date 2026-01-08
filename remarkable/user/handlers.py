# encoding: utf-8
import http
import logging
import os
import time

import peewee
import speedy.peewee_plus.orm
import tornado
from marshmallow import ValidationError, fields
from tornado.escape import parse_qs_bytes
from tornado.web import _ARG_DEFAULT, _ArgDefaultMarker
from utensils.crypto._sm4 import JHexSm4

from remarkable import config
from remarkable.base_handler import Auth, BaseHandler, DbQueryHandler, PermCheckHandler, route
from remarkable.common import field_validate
from remarkable.common.apispec_decorators import doc, use_kwargs
from remarkable.common.constants import ADMIN_ID, FeatureSchema, HistoryAction, get_perms
from remarkable.common.enums import NafmiiEventStatus, NafmiiEventType
from remarkable.common.util import generate_timestamp, rate_limit
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_permission import Permission
from remarkable.models.new_role import Role
from remarkable.models.new_role_permission import RolePermissionRef
from remarkable.models.new_user import NewAdminUser
from remarkable.models.new_user_role import UserRoleRef
from remarkable.models.query_helper import AsyncPagination
from remarkable.pw_models.model import NewFileProject, NewHistory
from remarkable.security import authtoken
from remarkable.security.crypto_util import encode_jwt, make_bearer_header
from remarkable.service.time_limit import TimeLimit
from remarkable.service.user import gen_password, gen_salt, update_user_refs, validate_password
from remarkable.session import encode_permission

logger = logging.getLogger(__name__)


class PermissionHelper:
    @staticmethod
    def check(permission):
        checked = {}
        for item in permission:
            if "perm" not in item or not isinstance(item["perm"], str):
                raise ValidationError(_("The request format is incorrect"))
            if item["perm"] not in get_perms():
                raise ValidationError(_("Unrecognized ") + "{}".format(item["perm"]))
            if item["perm"] in checked:
                raise ValidationError(_("Duplicate permissions in the request"))

            checked[item["perm"]] = item

    @staticmethod
    def ensure_valid_permission(origin_permission):
        have_model_manage, have_schema_manage = False, False
        for item in origin_permission:
            if item["perm"] == "manage_model":
                have_model_manage = True
            if item["perm"] == "manage_mold":
                have_schema_manage = True
        if have_model_manage and not have_schema_manage:
            # 有模型管理权限 需要有schema管理权限
            origin_permission.append({"perm": "manage_mold"})
        return origin_permission

    @staticmethod
    async def remove_not_exist_ids(permission):
        for item in permission:
            if "prj_filter" in item:
                item["prj_filter"] = await PermissionHelper.check_prj_id(item["prj_filter"])

    @staticmethod
    async def check_prj_id(prj_id_list):
        projects = await NewFileProject.find_by_ids([int(pid) for pid in prj_id_list])
        return [p.id for p in projects]


user_args = {
    "name": fields.String(required=True, validate=field_validate.Regexp(r"^.{1,128}$")),
    "password": fields.String(load_default="", allow_none=True),
    "permission": fields.List(fields.Dict(), load_default=[], validate=PermissionHelper.check),
    "note": fields.String(load_default="", allow_none=True),
    "expired_utc": fields.Integer(load_default=0),
}

role_args = {
    "name": fields.String(required=True),
    "description": fields.String(load_default=""),
}

permission_args = {
    "name": fields.String(required=True),
    "label": fields.String(required=True),
    "description": fields.String(load_default=""),
}


@route(r"/user")
class UserInfoHandler(DbQueryHandler):
    @Auth(["manage_user"])
    @use_kwargs(user_args, location="json")
    async def post(self, name, password, permission, note, expired_utc):
        if password and (msg := validate_password(password)):
            return self.error(_(msg), status_code=http.HTTPStatus.BAD_REQUEST)
        salt = gen_salt()
        password = gen_password(password, salt)
        sql_params = {
            "name": name,
            "password": password,
            "salt": salt,
            "permission": PermissionHelper.ensure_valid_permission(permission),
            "note": note,
            "expired_utc": expired_utc,
        }
        exists_user = await NewAdminUser.find_by_kwargs(name=name)
        if exists_user:
            return self.error(_("User is existed"))

        async with pw_db.atomic():
            await PermissionHelper.remove_not_exist_ids(permission)
            user = await NewAdminUser.create(**sql_params)
            await NewHistory.save_operation_history(
                user.id, self.current_user.id, HistoryAction.CREATE_USER.value, self.current_user.name, {"uid": user.id}
            )
        return self.data({"id": user.id, "name": name})

    @Auth(["manage_user"])
    @use_kwargs({"name": fields.Str(load_default=None), "note": fields.Str(load_default=None)}, location="query")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, name, note, page, size):
        cond = speedy.peewee_plus.orm.TRUE
        if not self.current_user.is_admin:
            cond &= NewAdminUser.id != 1
        if name:
            cond &= NewAdminUser.name.contains(name)
        if note:
            cond &= NewAdminUser.note.contains(note)
        query = NewAdminUser.select().where(cond).order_by(NewAdminUser.id.desc())
        data = await AsyncPagination(query, page=page, size=size).data()
        return self.data(data)


@route(r"/user/(\d+)")
class UserManage(PermCheckHandler):
    @Auth("manage_user")
    async def get(self, uid):
        user = await NewAdminUser.find_by_id(uid)
        if not user:
            return self.error(_("User not exists."))
        return self.data(user.to_dict())

    @Auth(["manage_user"])
    async def delete(self, uid):
        user = await NewAdminUser.find_by_id(uid)
        if not user:
            return self.error(_("User not exists."))
        if user.is_admin:
            return self.error(_("Can't delete admin account."))
        self.session_clear(user.id)
        await user.soft_delete()
        await NewHistory.save_operation_history(
            user.id, self.current_user.id, HistoryAction.DELETE_USER.value, self.current_user.name, {"uid": uid}
        )
        return self.data(None)

    @Auth(["manage_user"])
    @use_kwargs(user_args, location="json")
    async def put(self, uid, name, password, permission, note, expired_utc):
        user = await NewAdminUser.find_by_id(uid)
        if not user:
            return self.error(_("User not exists."))

        db_param = {"note": note or ""}  # admin仅允许有限地修改
        if not user.is_admin:
            if user.name != name:
                exists_user = await NewAdminUser.find_by_kwargs(name=name)
                if exists_user:
                    return self.error(_("User is existed"))
                db_param["name"] = name
                self.session_clear(user.id)

            if permission:
                await PermissionHelper.remove_not_exist_ids(permission)
                db_param["permission"] = PermissionHelper.ensure_valid_permission(permission)
                self.session_update(user.id, perm=permission)
            if expired_utc is not None:
                db_param["expired_utc"] = expired_utc

        if password:
            if msg := validate_password(password):
                return self.error(_(msg), status_code=http.HTTPStatus.BAD_REQUEST)
            salt = gen_salt()
            db_param["salt"] = salt
            db_param["password"] = gen_password(password, salt)
            if db_param["password"] != user.password:
                self.session_clear(user.id)

        if db_param:
            async with pw_db.atomic():
                await user.update_(**db_param)
                await NewHistory.save_operation_history(
                    user.id,
                    self.current_user.id,
                    HistoryAction.MODIFY_USER.value,
                    self.current_user.name,
                    {"uid": int(uid)},
                )
        return self.data(None)


@route(r"/login")
class LoginHandler(BaseHandler):
    args = {"name": fields.String(required=True), "password": fields.String(required=True)}

    def ip_limit(self):
        """限制同IP访问接口频率"""
        addr = self.request.headers.get("X-Real-IP") or self.request.remote_ip
        return rate_limit(addr, "login_limit")

    @use_kwargs(args, location="json")
    async def post(self, name, password):
        # if self.ip_limit():
        #     return self.error(_("Interface access frequency is too fast, please try again later"))
        if TimeLimit.check(self):
            return self.error(
                _("The system access has expired, please contact the administrator."),
                status_code=http.HTTPStatus.PAYMENT_REQUIRED,
            )

        user = await NewAdminUser.find_by_kwargs(name=name)
        if not user:
            fail_count = int(self.session["_fail_count"] or "0")
            self.session["_fail_count"] = fail_count + 1
            self.session_sync()

            if max(fail_count, self.silence_tries) >= config.get_config("app.max_fail_count", 10):
                return self.error(_("The password input error has reached the upper limit."))
            return self.error(_("Incorrect user or password!"))

        if user.expired_utc and user.expired_utc < int(time.time()):
            return self.error(_("Account has expired."))

        login_pass = gen_password(password, user.salt)
        if login_pass != user.password:
            fail_count = int(self.session["_fail_count"] or "0")
            self.session["_fail_count"] = fail_count + 1
            self.session_sync()

            if max(fail_count, self.silence_tries) >= config.get_config("app.max_fail_count", 10):
                return self.error(_("The password input error has reached the upper limit."))
            return self.error(_("Incorrect user or password!"))

        self.session["uid"] = user.id
        self.session["ext_id"] = user.ext_id if user.ext_id else ""
        if config.get_config("web.xsrf_cookies"):
            self.session["xsrf_token"] = self.xsrf_token
        # 记录ip
        self.session["ip"] = self.request.headers.get("X-Real-IP") or self.request.remote_ip
        # 存用户名
        self.session["name"] = name
        # 存权限
        self.session["perm"] = encode_permission(user.permission)
        # 重置错误登录计数
        self.session["_fail_count"] = 0
        self.session_sync()

        # 同一账号在多地尝试登录, 即使密码正确, 但超限也应该限制该账户登录
        if self.silence_tries >= config.get_config("app.max_fail_count", 10):
            return self.error(_("Your account has reached the max number of logins, please try again later"))

        await user.update_(login_count=user.login_count + 1, login_utc=generate_timestamp())
        await NewHistory.save_operation_history(
            None,
            user.id,
            HistoryAction.LOGIN.value,
            name,
            meta=None,
            nafmii=self.get_nafmii_event(type=NafmiiEventType.LOGIN.value, status=NafmiiEventStatus.SUCCEED.value),
        )
        return self.data({})


@route(r"/user/me")
class UserMeHandler(BaseHandler):
    @doc(
        summary="Get current user info",
        tags=["user"],
        description="传入jwt参数则额外返回jwt token（有效期1h），用于其他系统登录验证",
    )
    @Auth("browse")
    @use_kwargs({"jwt": fields.Bool(load_default=False)}, location="query")
    async def get(self, jwt):
        if TimeLimit.check(self):
            return self.error(
                _("The system access has expired, please contact the administrator."),
                status_code=http.HTTPStatus.PAYMENT_REQUIRED,
            )
        meta_data = self.current_user.data or {}
        res = {
            "id": self.current_user.id,
            "name": self.current_user.name,
            "perm": self.current_user.permission,
            "group_name": meta_data.get("group_name", ""),
            "oa_user": meta_data.get("oa_user", ""),
            "param_perms": meta_data.get("param_perms", []),
            "ext_id": self.current_user.ext_id,
            "_xsrf": bytes.decode(self.xsrf_token),
        }
        if jwt:
            jwt_secret_key = get_config("app.jwt_secret_key")
            if not jwt_secret_key:
                return self.error("JWT Unsupported", status_code=http.HTTPStatus.BAD_REQUEST)
            res["jwt"] = make_bearer_header(
                encode_jwt({"sub": res["ext_id"] or res["name"], "exp": time.time() + 3600}, jwt_secret_key)
            ).pop("Authorization")

        return self.data(res)

    def check_xsrf(self):
        """we do not need to check xsrf here"""


@route(r"/user/unify-login")
class UserUnifyLoginHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.arguments_before_obs = self.query_before_obs = None
        obs = super().get_argument("obs", None)
        if obs:
            try:
                self.query_before_obs = JHexSm4.decrypt(obs, get_config("web.hex_binary_key"))
                self.arguments_before_obs = parse_qs_bytes(self.query_before_obs, keep_blank_values=True)
            except Exception as e:
                logger.exception(e)

    def get_argument(
        self,
        name: str,
        default: None | str | _ArgDefaultMarker = _ARG_DEFAULT,
        strip: bool = True,
    ) -> str | None:
        if self.arguments_before_obs is not None:
            return self._get_argument(name, default, self.arguments_before_obs, strip)
        return self._get_argument(name, default, self.request.arguments, strip)

    async def get(self):
        ext_id = self.get_argument("uid", None)
        assert ext_id, tornado.web.HTTPError(400, "uid(as 'ext_id' on our side) is required")

        url = self.request.full_url()
        if "X-Original-Request-URI" in self.request.headers:
            url = self.request.headers["X-Original-Request-URI"]
        if self.query_before_obs:
            url = f"{url.split('?')[0]}?{self.query_before_obs.decode()}"
        if not (authtoken.validate_url(url, exclude_domain=True)[0]):
            raise tornado.web.HTTPError(401, "Unauthorized")

        ext_sys = self.get_argument("ext_sys", None)
        ext_uname = self.get_argument("ext_uname", ext_id)
        username = self.get_argument("username", ext_uname)
        department = self.get_argument("department", None)
        department_id = self.get_argument("department_id", None)
        perms = self.get_argument("permission", None) or ""
        business_system_code = self.get_argument("business_system_code", None)
        feature = FeatureSchema.from_config()
        perms = feature.filter_perms_to_db({p.strip() for p in perms.split(",") if p})

        data = {}
        if oa_user := self.get_argument("oa_user", ""):
            data["oa_user"] = oa_user

        # 中信证券托管部权限
        # https://gitpd.paodingai.com/cheftin/docs_trident/-/issues/254#note_456285
        if group_name := self.get_argument("group_name", ""):
            data["group_name"] = group_name
        parameter_permission = self.get_argument("parameter_permission", "")
        if param_perms := sorted({p.strip() for p in parameter_permission.split(",") if p}):
            data["param_perms"] = param_perms

        if user := await self.existed_user(ext_id, username):
            user.name = username
            user.ext_id = ext_id
            user.login_utc = generate_timestamp()
            # 确保`admin`权限不被覆盖
            user.permission = feature.all_perms_to_db() if user.is_admin else perms
            user.login_count += 1
            user.data = data
            if not user.department_id:
                user.department = department
                user.department_id = department_id
            await pw_db.update(user)
        else:
            user = await NewAdminUser.create(
                name=username,
                permission=perms,
                ext_id=ext_id,
                ext_from=ext_sys,
                password="",
                salt="",
                department=department,
                department_id=department_id,
                data=data,
            )

        await update_user_refs(user.id, group_ids=business_system_code)

        self.set_secure_cookie("from_trident", "1", httponly=True)
        self.session["from_trident"] = "1"
        self.session["uid"] = user.id
        self.session["perm"] = encode_permission(user.permission)
        self.session["name"] = str(username)
        self.session["ext_id"] = ext_id
        if config.get_config("web.xsrf_cookies"):
            self.session["xsrf_token"] = self.xsrf_token
        self.session_sync()
        origin = self.get_argument("origin", "")

        # 星云系统用户登录之后需要清掉cookie中的pid, 不然只能看一个project的任务
        if get_config("client.name") == "chinaamc_yx":
            self.clear_cookie("pid")

        redirect_url = origin or self.get_argument("redirect", "")

        # elif not redirect_url:
        #     iframe_url = ""
        #     url_map = {
        #         r"^schema$": "#/schema",
        #         r"^model$": "#/szse/model-list",
        #         r"^file$": "#/szse/label-file-list",
        #     }
        #
        #     if origin:
        #         for reg, url in url_map.items():
        #             matched = re.search(reg, origin)
        #             if matched:
        #                 iframe_url = f"{url}"
        #                 break
        #     project_group_id = self.get_argument("project_group_id", "")
        #     if project_group_id:
        #         join_char = "&" if query else "?"
        #         param = f"{join_char}project_group_id={project_group_id}"
        #         query += param
        #
        #     redirect_url = f"/{iframe_url}{query}"

        logging.debug(f"Redirecting to: {redirect_url}")
        await NewHistory.save_operation_history(
            None,
            action=HistoryAction.LOGIN,
            uid=user.id,
            user_name=user.name,
            meta=None,
            nafmii=self.get_nafmii_event(
                status=NafmiiEventStatus.SUCCEED.value,
                type=NafmiiEventType.LOGIN.value,
                content="登录成功",
            ),
        )
        return self.redirect(redirect_url or "/")

    @staticmethod
    async def existed_user(ext_id: str, username: str) -> NewAdminUser | None:
        admin_user = await NewAdminUser.find_by_id(ADMIN_ID)
        if (ext_id and ext_id == "admin") or (username and username == "admin"):
            return admin_user
        if user := await NewAdminUser.find_by_kwargs(ext_id=ext_id):
            return user
        # 先部署scriber, 后部署trident, 会存在没有`ext_id`的用户，这里通过`name`查询。
        if user := await pw_db.first(
            NewAdminUser.select().where(NewAdminUser.name == username, NewAdminUser.ext_id.is_null())
        ):
            return user


@route(r"/user/login/by_token")
class TokenLoginHandler(BaseHandler):
    async def get(self):
        if TimeLimit.check(self):
            return self.error(
                _("The system access has expired, please contact the administrator."),
                status_code=http.HTTPStatus.PAYMENT_REQUIRED,
            )

        url = self.request.full_url()
        if "X-Original-Request-URI" in self.request.headers:
            url = self.request.headers["X-Original-Request-URI"]
        app_id = config.get_config("app.auth.label.app_id")
        secret_key = config.get_config("app.auth.label.secret_key")
        token_expire = config.get_config("app.auth.label.token_expire")
        env = os.environ.get("ENV") or "dev"
        token_passed, msg = authtoken.validate_url(url, app_id, secret_key, token_expire)
        if env != "dev" and not token_passed:
            logging.error(msg)
            raise tornado.web.HTTPError(403)
        user_id = self.get_argument("uid", None)
        user_group = self.get_argument("group", None)
        if not user_id or not user_group:
            raise tornado.web.HTTPError(403)
        app_name = config.get_config("app.app_id")
        self.set_secure_cookie("{}_user_group".format(app_name), str(user_group))


@route(r"/logout")
class LogoutHandler(BaseHandler):
    @Auth("browse")
    async def post(self):
        return await self._logout()

    async def get(self):
        return await self._logout()

    async def _logout(self):
        user = self.current_user
        from_trident = bool(self.session["from_trident"])
        self.session_clear()

        if user is not None:
            await NewHistory.save_operation_history(
                None,
                user.id,
                HistoryAction.NAFMII_DEFAULT.value,
                user.name,
                meta=None,
                nafmii=self.get_nafmii_event(
                    request=self.request,
                    status=NafmiiEventStatus.SUCCEED.value,
                    type=NafmiiEventType.LOGOUT.value,
                    menu="退出登录",
                    content="退出登录成功",
                ),
            )
        if from_trident:
            return self.logout_trident()
        return self.data({})

    def logout_trident(self):
        to_url = authtoken.encode_url(
            url=f"{config.get_config('app.auth.trident.url')}/api/v1/user/logout",
            app_id=config.get_config("app.auth.trident.app_id"),
            secret_key=config.get_config("app.auth.trident.secret_key"),
            params={"ext_uname": self.current_user.name if self.current_user else "_no_user_resu_on_"},
            exclude_domain=True,
        )
        if self.request.method == "GET":
            self.redirect(to_url)

        return self.data({"redirect_url": to_url})

    def on_finish(self):
        # 注销动作完成后不再需要刷新session
        pass


@route(r"/department")
class DepartmentHandler(BaseHandler):
    @Auth("browse")
    async def get(self):
        data = []
        users = await NewAdminUser.find_by_kwargs(delegate="all")
        department_map = {user.department_id: user.department for user in users}
        for department_id, department in department_map.items():
            data.append({"department_id": department_id, "department": department})
        return self.data(data)


@route("/roles")
class RolesHandler(BaseHandler):
    @Auth("manage_user")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page, size):
        query = Role.select().order_by(Role.id.desc())
        res = await AsyncPagination(query, page, size).data()
        return self.data(res)

    @Auth("manage_user")
    @use_kwargs(role_args, location="json")
    async def post(self, name, description):
        try:
            role = await Role.create(name=name, description=description)
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error(_("name is duplicated"))
        return self.data(role.to_dict())


@route(r"/roles/(\d+)")
class RoleHandler(BaseHandler):
    @Auth("manage_user")
    @use_kwargs(role_args, location="json")
    async def put(self, role_id, name, description):
        try:
            await Role.update_by_pk(role_id, name=name, description=description)
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error(_("name is duplicated"))

        return self.data({})

    @Auth("manage_user")
    async def delete(self, role_id):
        if not (role := await Role.find_by_id(role_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        await pw_db.delete(role)
        return self.data({})


@route("/permissions")
class PermissionsHandler(BaseHandler):
    @Auth("manage_user")
    @use_kwargs(AsyncPagination.web_args, location="query")
    async def get(self, page, size):
        query = Permission.select().order_by(Permission.id.desc())
        res = await AsyncPagination(query, page, size).data()
        return self.data(res)

    @Auth("manage_user")
    @use_kwargs(permission_args, location="json")
    async def post(self, name, label, description):
        try:
            permission = await Permission.create(name=name, label=label, description=description)
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error(_("name is duplicated"))
        return self.data(permission.to_dict())


@route(r"/permissions/(\d+)")
class PermissionHandler(BaseHandler):
    @Auth("manage_user")
    @use_kwargs(permission_args, location="json")
    async def put(self, permission_id, name, label, description):
        try:
            await Permission.update_by_pk(permission_id, name=name, label=label, description=description)
        except peewee.IntegrityError as exp:
            logger.exception(str(exp))
            return self.error(_("name is duplicated"))

        return self.data({})

    @Auth("manage_user")
    async def delete(self, permission_id):
        if not (permission := await Permission.find_by_id(permission_id)):
            return self.error(_("Item not found"), status_code=http.HTTPStatus.NOT_FOUND)

        await pw_db.delete(permission)
        return self.data({})


@route(r"/roles/(\d+)/permissions")
class RolePermissionRefHandler(BaseHandler):
    @Auth("manage_user")
    async def get(self, role_id):
        query = (
            RolePermissionRef.select(RolePermissionRef, Permission.label.alias("permission_label"))
            .join(Permission)
            .where(RolePermissionRef.role_id == role_id)
        )
        ret = await pw_db.execute(query.dicts())
        return self.data({"items": list(ret)})

    @Auth("manage_user")
    @use_kwargs({"permission_ids": fields.List(fields.Int())}, location="json")
    async def post(self, role_id, permission_ids):
        query = RolePermissionRef.select().where(RolePermissionRef.role_id == role_id)
        exist_permissions = await pw_db.execute(query)

        exist_permission_ids = [permission_ref.permission_id for permission_ref in exist_permissions]
        permissions_to_add = set(permission_ids) - set(exist_permission_ids)
        permissions_to_rm = set(exist_permission_ids) - set(permission_ids)

        delete_cond = RolePermissionRef.role_id == role_id
        delete_cond &= RolePermissionRef.permission_id.in_(permissions_to_rm)
        permission_infos = [
            {"role_id": role_id, "permission_id": permission_id} for permission_id in permissions_to_add
        ]
        async with pw_db.atomic():
            await pw_db.execute(RolePermissionRef.delete().where(delete_cond))
            await RolePermissionRef.bulk_insert(permission_infos)

        return self.data({})


@route(r"/users/(\d+)/roles")
class UserRoleRefHandler(BaseHandler):
    @Auth("manage_user")
    async def get(self, user_id):
        query = (
            UserRoleRef.select(UserRoleRef, Role.name.alias("role_name"))
            .join(Role)
            .where(UserRoleRef.user_id == user_id)
        )
        ret = await pw_db.execute(query.dicts())
        return self.data({"items": list(ret)})

    @Auth("manage_user")
    @use_kwargs({"role_ids": fields.List(fields.Int())}, location="json")
    async def post(self, user_id, role_ids):
        query = UserRoleRef.select().where(UserRoleRef.user_id == user_id)
        exist_roles = await pw_db.execute(query)

        exist_role_ids = [user_role.role_id for user_role in exist_roles]
        roles_to_add = set(role_ids) - set(exist_role_ids)
        roles_to_rm = set(exist_role_ids) - set(role_ids)

        delete_cond = UserRoleRef.user_id == user_id
        delete_cond &= UserRoleRef.role_id.in_(roles_to_rm)
        role_infos = [{"user_id": user_id, "role": role_id} for role_id in roles_to_add]
        async with pw_db.atomic():
            await pw_db.execute(UserRoleRef.delete().where(delete_cond))
            await UserRoleRef.bulk_insert(role_infos)

        return self.data({})
