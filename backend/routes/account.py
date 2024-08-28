import aiotieba
from pydantic import BaseModel
from sanic import Blueprint
from sanic_ext import validate
from sanic_jwt import inject_user, scoped

from core.enum import Permission
from core.exception import ArgException
from core.models import User
from core.types import TBRequest
from core.utils import json, validate_password

bp_account = Blueprint("account", url_prefix="/account")


@bp_account.get("/portrait")
@inject_user()
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_portrait(rqt: TBRequest, user: User):
    """获取用于获取贴吧用户头像的portrait值

    """
    async with aiotieba.Client() as client:
        _user = await client.get_user_info(user.UID)
    return json(data=_user.portrait)


class FirstLogin(BaseModel):
    password: str
    BDUSS: str
    STOKEN: str


@bp_account.post("/login/first")
@validate(form=FirstLogin)
async def first_login_api(rqt: TBRequest, body: FirstLogin):
    """第一次登录接口

    用于第一次登录时填入初始化设置信息
    """
    if not rqt.app.ctx.config.first_start:
        return json("您不是第一次登录了", status_code=403)

    validate_password(body.password)

    async with aiotieba.Client(body.BDUSS, body.STOKEN) as client:
        user = await client.get_self_info()

    await User.create(
        user_id=user.user_id,
        UID=user.tieba_uid,
        username=user.user_name,
        password=rqt.app.ctx.password_hasher.hash(body.password),
        enable_login=True,
        BDUSS=body.BDUSS,
        STOKEN=body.STOKEN,
    )

    with rqt.app.ctx.config:
        rqt.app.ctx.config.first_start = False
    return json("成功创建超级管理员")


@bp_account.post("/password/update")
@inject_user()
@scoped(Permission.GE_ORDINARY.scopes, False)
async def change_password(rqt: TBRequest, user: User):
    """用于修改自己密码的接口


    """
    if not rqt.form.get("password"):
        raise ArgException

    validate_password(rqt.form.get("password"))
    user.password = rqt.app.ctx.password_hasher.hash(rqt.form.get('password'))
    await user.save()
    return json("修改密码成功")

