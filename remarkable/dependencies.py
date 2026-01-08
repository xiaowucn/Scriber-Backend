import datetime
import http
import logging
from typing import Iterable, Type

import jwt
from fastapi import Body, Depends, HTTPException, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_permissions import Authenticated, Everyone, configure_permissions
from peewee import ManyToManyField, Select
from starlette.requests import Request

from remarkable import config
from remarkable.db import pw_db
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.base import TModel
from remarkable.schema import TSchema
from remarkable.session import SessionManager

logger = logging.getLogger(__name__)


def _validate_exp(exp) -> None:
    try:
        exp = int(exp)
    except ValueError:
        raise HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST, detail="Expiration Time claim (exp) must be an integer."
        ) from None

    if exp <= datetime.datetime.now(tz=datetime.timezone.utc).timestamp():
        raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail="Token has expired")


async def get_current_user(
    request: Request,
    _: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> NewAdminUser:
    if "session" not in request.scope:
        request.scope["session"] = SessionManager(request)

    if request.session.session_map:  # noqa
        user = await NewAdminUser.get_by_id(int(request.session.user_id))  # noqa
    else:
        user = None

    # JWT 可能存在于请求头或者请求参数中
    auth_token = request.headers.get("Authorization") or request.query_params.get("bearer_token") or ""
    if auth_token and (secret_key := config.get_config("app.jwt_secret_key")):
        if (parts := auth_token.split()) and len(parts) == 2 and parts[0].lower() == "bearer":  # 验证头部信息
            try:
                payload = jwt.decode(parts[-1], secret_key, algorithms=["HS256"])  # 解码JWT
                if exp := payload.get("exp"):
                    _validate_exp(exp)
            except jwt.DecodeError:
                raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail="JWT decode error") from None
            except jwt.ExpiredSignatureError as e:
                raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail=str(e)) from None
            except ValueError as e:
                raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail=str(e)) from None

            if sub := payload.get("sub"):
                user = await pw_db.first(
                    NewAdminUser.select()
                    .where((NewAdminUser.ext_id == sub) | (NewAdminUser.name == sub))
                    .order_by(NewAdminUser.ext_id.desc())
                )
                if not user:
                    raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail="User is not active")
                request.scope["session"]["uid"] = user.id

        if user is None:
            raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="JWT token: User not found")

    if simple_token := request.headers.get("access-token"):
        if simple_token == config.get_config("app.simple_token"):
            request.scope["session"]["uid"] = 1
            logger.warning("Using simple token will be deprecated in the future, please use JWT instead.")
            user = await NewAdminUser.get_by_id(1)

        if user is None:
            raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail="Token validation failed")

    if user is None:
        raise HTTPException(status_code=http.HTTPStatus.UNAUTHORIZED, detail="Not authenticated")

    return user


async def get_active_principals(user: NewAdminUser = Depends(get_current_user)) -> list[str]:
    principals = [Everyone]
    if user:
        principals.append(Authenticated)
        principals.extend(await user.principals())
        # TODO: 根据旧的权限分组，添加更细致的权限控制
        return principals
    return principals


Permission = configure_permissions(get_active_principals)


def model_with_perm(
    clz: Type[TModel],  # noqa: UP006
    *prefetch: Iterable[Select],
    alias: str | None = None,
    action: str = "view",
    schema_clz: Type[TSchema] | None = None,  # noqa: UP006
    fields: tuple[str, ...] = (),
    **options,
):
    async def get_record(model_id: int = Path(..., alias=alias)) -> TModel:
        # prefetch 在 peewee BaseModel 中是单个参数. 此处和港交所分支不一致, 港交所分支prefetch最多传一项, 但该项可以是列表...
        record = await clz.get_by_id(model_id, prefetch, fields=fields, **options)
        if record is None:
            raise HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND,
                detail=f"{clz.table_name()}({model_id}) not found, or deleted?",
            )
        return record

    def schema_to_model(schema_ins: schema_clz = Body(..., alias=alias)) -> TModel:
        # TODO: 存在多对多关系的字段时，实例化时触发了不必要的数据库操作，先略过。
        # https://github.com/coleifer/peewee/issues/2765
        db_fields = {i for i in clz._meta.sorted_field_names if not isinstance(getattr(clz, i), ManyToManyField)}
        return clz(**schema_ins.model_dump(exclude={i for i in schema_ins.model_fields_set if i not in db_fields}))

    return Permission(action, get_record if schema_clz is None else schema_to_model)


def model_by_cond_with_perm(
    clz: Type[TModel],  # noqa: UP006
    clz_field,
    *prefetch: Iterable[Select],
    alias: str | None = None,
    action: str = "view",
    fields: tuple[str, ...] = (),
    **options,
):
    async def get_record(model_id: int = Path(..., alias=alias)) -> TModel:
        record = await clz.get_by_cond(clz_field == model_id, prefetch, fields=fields, **options)
        if record is None:
            raise HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND,
                detail=f"{clz.table_name()}({model_id}) not found, or deleted?",
            )
        return record

    return Permission(action, get_record)


async def pw_transaction() -> None:
    async with pw_db.atomic():
        yield


def check_user_permission(*perms: str):
    async def get_user(user: NewAdminUser = Depends(get_current_user)) -> NewAdminUser:
        for perm in perms:
            if f"perm:{perm}" in await user.principals():
                break
        else:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail="No permission")
        return user

    return get_user


def check_any_permissions(*perms: str):
    async def get_user(user: NewAdminUser = Depends(get_current_user)) -> NewAdminUser:
        if not ({f"perm:{perm}" for perm in perms} & set(await user.principals())):
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN, detail="No permission")
        return user

    return get_user


def get_nafmii_event(request: Request, **kwargs):
    from user_agents import parse

    user_agent = parse(request.headers.get("User-Agent", ""))

    remote_ip = request.headers.get("X-Real-IP") or request.client.host
    return {
        "ip": remote_ip,
        "client": f"{user_agent.browser.family} {user_agent.browser.version_string}",
        **kwargs,
    }
