from typing import Optional

from aiotieba import Client
from aiotieba.api._classdef import UserInfo
from pydantic import BaseModel
from sanic import Blueprint, Request
from sanic_ext import validate
from sanic_jwt import scoped

from core.enum import Permission
from core.exception import ExecutorNotFoundError, Unauthorized, ArgException
from core.models import User, ForumPermission
from core.types import TBRequest
from core.utils import json, validate_password

bp_manager = Blueprint("manager", url_prefix="/manager")


@bp_manager.get("/user/all")
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_users(rqt: Request):
    users = await User.all()
    users_dict = [user.to_json() for user in users]
    return json(data=users_dict)


class UserFrom(BaseModel):
    user: str = None
    password: str = None
    enable_login: bool = False
    BDUSS: str = ""
    STOKEN: str = ""


@bp_manager.post("/user/update")
@validate(form=UserFrom)
@scoped(Permission.GE_SUPER_ADMIN.scopes, False)
async def update_user(rqt: TBRequest, body: UserFrom):
    if body.user is None and body.BDUSS == "":
        raise ArgException("user和BDUSS参数需有其一")

    if body.password is None or body.password == "":
        pwd = None
    else:
        validate_password(body.password)
        pwd = rqt.app.ctx.password_hasher.hash(body.password)

    if body.BDUSS != "":
        async with Client(body.BDUSS, body.STOKEN) as client:
            tb_user = await client.get_self_info()
    else:
        tb_user: Optional[UserInfo] = None

    if tb_user is None:
        fp = await ForumPermission.get_or_none(is_executor=True)
        if fp is None:
            raise ExecutorNotFoundError
        user = await fp.user.get()
        async with Client(user.BDUSS, user.STOKEN) as client:
            tb_user: UserInfo = await client.get_user_info(body.user)

    user = await User.get_or_none(user_id=tb_user.user_id)
    if user is None:
        uid = tb_user.tieba_uid
        user = await User.create(
            user_id=tb_user.user_id,
            UID=None if uid == 0 else uid,
            username=tb_user.user_name,
            showname=tb_user.show_name,
            enable_login=body.enable_login,
            password=pwd,
            BDUSS=body.BDUSS,
            STOKEN=body.STOKEN,
        )
    else:
        body.password = pwd
        user = await user.update_from_dict(body.dict())

    return json(data=user.to_json())


@bp_manager.post("/user/delete/<user_id>")
@scoped(Permission.GE_SUPER_ADMIN.scopes, False)
async def delete_user(rqt: TBRequest, user_id: str):
    fp = await ForumPermission.get_or_none(user_id=user_id, permission=Permission.MASTER.value)
    if fp is not None:
        raise Unauthorized

    fp_query_set = ForumPermission.filter(user_id=user_id)
    fps = await fp_query_set.all()
    user_query_set = User.filter(user_id=user_id)
    user = await user_query_set.get_or_none()

    await fp_query_set.delete()
    await user_query_set.delete()
    if user is None:
        return json(data=None)
    else:
        data = user.to_json()
        data["permissions"] = [fp.to_json() for fp in fps]
        return json(data=data)


@bp_manager.get("/permission/all")
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_permission(rqt: TBRequest):
    fps = await ForumPermission.all()
    fps_dict = [i.to_json() for i in fps]
    return json(data=fps_dict)


class PermissionForm(BaseModel):
    user_id: str
    forum: str
    permission: int = Permission.ORDINARY.value
    tb_permission: int = Permission.ORDINARY.value
    is_executor: bool = False


@bp_manager.post("/permission/update")
@validate(form=PermissionForm)
@scoped(Permission.GE_SUPER_ADMIN.scopes, False)
async def update_permission(rqt: TBRequest, body: PermissionForm):
    if body.permission == Permission.MASTER or body.tb_permission == Permission.MASTER:
        raise Unauthorized

    fp = await ForumPermission.get_or_none(user_id=body.user_id, forum=body.forum)
    if fp is None:
        await ForumPermission.create(**body.dict())
    else:
        fp = await fp.update_from_dict(body.dict())
    return json(data=fp.to_json())


class DelFPForm(BaseModel):
    user_id: str
    forum: str


@bp_manager.post("/permission/delete")
@validate(form=DelFPForm)
@scoped(Permission.GE_SUPER_ADMIN.scopes, False)
async def delete_permission(rqt: TBRequest, body: DelFPForm):
    fp = await ForumPermission.get_or_none(**body.dict())
    if fp is None:
        return json()
    else:
        if fp.permission == Permission.MASTER:
            raise Unauthorized

        await fp.delete()
        return json(data=fp.to_json())
