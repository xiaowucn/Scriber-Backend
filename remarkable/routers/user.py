import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from remarkable import config
from remarkable.common.constants import FeatureSchema
from remarkable.db import pw_db
from remarkable.models.new_user import NewAdminUser
from remarkable.plugins.cgs.scripts.cgs_demo import generate_timestamp
from remarkable.routers.schemas.user import RosterLoginSchema
from remarkable.security import authtoken
from remarkable.session import SessionManager, encode_permission

user_router = APIRouter(prefix="/user", tags=["User"])
logger = logging.getLogger(__name__)


async def login_user(request: Request, user: NewAdminUser, response: Response):
    request.scope["session"] = SessionManager(response)
    request.session["uid"] = user.id
    request.session["perm"] = encode_permission(user.permission)
    request.session["name"] = str(user.name)
    request.session.set()
    request.session.refresh()
    request.scope["skip_set_cookie"] = True  # 跳过session中间件


@user_router.get("/roster-login", include_in_schema=False)
async def roster_login(request: Request, form: RosterLoginSchema = Depends()):
    if "X-Original-Request-URI" in request.headers:
        url = request.headers["X-Original-Request-URI"]
    elif "X-Real-FULLURL" in request.headers:
        url = request.headers["X-Real-FULLURL"]
    else:
        url = str(request.url)

    app_id = config.get_config("app.auth.roster.app_id")
    secret = config.get_config("app.auth.roster.secret_key")
    token_expire = config.get_config("app.auth.roster.token_expire") or 300

    token_passed, msg = authtoken.validate_url(url, app_id, secret, token_expire)
    if not token_passed:
        logger.error(f"roster-login failed: {msg=}")
        raise HTTPException(401, "Unauthorized")

    feature = FeatureSchema.from_config()
    permission = feature.all_perms_to_db() if form.permission == "admin" else feature.base_perms_to_db()
    ext_from = "roster"
    user = await NewAdminUser.get_by_cond((NewAdminUser.ext_from == ext_from) & (NewAdminUser.name == form.cn))
    if not user:
        user = await NewAdminUser.create(
            name=form.cn,
            permission=permission,
            ext_id=form.cn,
            ext_from=ext_from,
            login_count=0,
            password="",
            salt="",
        )
    user.login_utc = generate_timestamp()
    user.permission = permission
    user.login_count += 1
    await pw_db.update(user)

    response = RedirectResponse(url=form.url or config.get_config("web.redirect_subpath", "/") or "/")
    await login_user(request, user, response)
    return response
