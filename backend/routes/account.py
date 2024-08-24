import aiotieba
from sanic import Blueprint
from sanic_jwt import inject_user, scoped

from core.enum import Permission
from core.exception import ArgException, FirstLoginError
from core.models import User
from core.types import TBRequest
from core.utils import json, validate_password

bp_account = Blueprint("account", url_prefix="/api/auth")


@bp_account.get("/portrait")
@inject_user()
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_portrait(rqt: TBRequest, user: User):
    """获取用于获取贴吧用户头像的portrait值

    """
    async with aiotieba.Client() as client:
        _user = await client.get_user_info(user.UID)
    return json(data=_user.portrait)


@bp_account.post("/first_login")
async def first_login_api(rqt: TBRequest):
    """第一次登录接口

    用于第一次登录时填入初始化设置信息
    """
    if not rqt.app.ctx.config["first_start"]:
        raise FirstLoginError(rqt.app.ctx.config["first_start"])
    if not (rqt.form.get('BDUSS') and rqt.form.get('fname')
            and rqt.form.get('password') and rqt.form.get('STOKEN')):
        raise ArgException
    validate_password(rqt.form.get('password'))

    try:
        async with aiotieba.Client(rqt.form.get('BDUSS'), rqt.form.get('STOKEN')) as client:
            user = await client.get_self_info()
    except ValueError as e:
        raise ArgException(e.args[0])
    await User.create(
        user_id=user.user_id,
        UID=user.tieba_uid,
        username=user.user_name,
        password=rqt.app.ctx.password_hasher.hash(rqt.form.get('password')),
        BDUSS=rqt.form.get('BDUSS'),
        STOKEN=rqt.form.get('STOKEN'),
        permission=Permission.MASTER
    )
    with rqt.app.ctx.config:
        rqt.app.ctx.config["first_start"] = False
    return json("成功创建超级管理员")


@bp_account.post("/change_pwd")
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


@bp_account.get("/self_full")
@inject_user()
@scoped(Permission.GE_ORDINARY.scopes, False)
async def get_self_full(rqt: TBRequest, user: User):
    """获取完整个人信息

    """
    user = await User.get(user_id=user.user_id)
    return json(data=user.to_json())
