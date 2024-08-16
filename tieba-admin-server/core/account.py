import aiotieba
from sanic import Blueprint, Request
from sanic_jwt import inject_user, protected, scoped

from core.enum import Permission
from core.exception import ArgException, FirstLoginError
from core.models import User, ForumUserPermission
from core.utils import json, validate_password

bp_account = Blueprint("account", url_prefix="/api/auth")


@bp_account.get("/portrait")
@inject_user()
@protected()
@scoped(Permission.min(), False)
async def get_portrait(rqt: Request, user: User):
    """获取用于获取贴吧用户头像的portrait值

    """
    async with aiotieba.Client() as client:
        _user = await client.get_user_info(user.uid)
    return json(data=_user.portrait)


@bp_account.post("/first_login")
async def first_login_api(rqt: Request):
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
            fid = await client.get_fid(rqt.form.get('fname'))
    except ValueError as e:
        raise ArgException(e.args[0])
    user = await User.create(
        uid=user.user_id,
        tuid=user.tieba_uid,
        username=user.user_name,
        password=rqt.app.ctx.password_hasher.hash(rqt.form.get('password')),
        BDUSS=rqt.form.get('BDUSS'),
        STOKEN=rqt.form.get('STOKEN'),
    )
    await ForumUserPermission.create(
        fid=fid,
        fname=rqt.form.get('fname'),
        user=user,
        permission=Permission.Master.value,
    )
    with rqt.app.ctx.config:
        rqt.app.ctx.config["first_start"] = False
    return json("成功创建超级管理员")


@bp_account.post("/change_pwd")
@inject_user()
@protected()
@scoped(Permission.ordinary(), False)
async def change_password(rqt: Request, user: User):
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
@protected()
@scoped(Permission.ordinary(), False)
async def get_self_full(rqt: Request, user: User):
    """获取完整个人信息

    """
    fup = await ForumUserPermission.get(user_id=user.uid)
    return json(data=await fup.to_dict())
