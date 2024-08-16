import aiotieba
from sanic import Blueprint, Request
from sanic.views import HTTPMethodView
from sanic_jwt import protected, scoped, inject_user

from .enum import Permission, ExecuteType
from .exception import ArgException
from .models import ForumUserPermission, User, ExecuteLog
from .utils import json, arg2user_info, validate_password

bp_manager = Blueprint("manager", url_prefix="/api/manager")


class UserPermission(HTTPMethodView):
    @protected()
    @scoped(Permission.min(), False)
    async def get(self, rqt: Request):
        _permission = await ForumUserPermission.all()
        permission = []
        for p in _permission:
            permission.append(await p.to_dict())
        return json(data=permission)

    @inject_user()
    @protected()
    @scoped(Permission.super(), False)
    async def post(self, rqt: Request, user: User):
        if not rqt.form.get("user") or not rqt.form.get("forum") or not rqt.form.get("pm"):
            raise ArgException
        if rqt.form.get("pm") not in [i.value for i in Permission]:
            raise ArgException

        try:
            async with aiotieba.Client() as client:
                user_info = await arg2user_info(client, rqt.form.get("user"), aiotieba.enums.ReqUInfo.ALL)
                forum_id = await client.get_fid(rqt.form.get("forum"))

            if rqt.form.get("del", "0") == "1":
                await ForumUserPermission.filter(user_id=user_info.user_id, fid=forum_id).delete()
                await User.filter(uid=user_info.user_id).delete()
                await ExecuteLog.create(user=user.username,
                                        type=ExecuteType.PermissionEdit,
                                        obj=user_info.user_name,
                                        note=f"删除用户[{user_info.user_name}]")
                return json(f"已删除{user_info.user_name}")

            permission = await ForumUserPermission.filter(user_id=user_info.user_id, fid=forum_id).get_or_none()
            if not permission:
                permission = await ForumUserPermission(user_id=user_info.user_id,
                                                       fid=forum_id,
                                                       permission=rqt.form.get("pm"),
                                                       fname=rqt.form.get("forum"))
                if permission.permission == Permission.Master.value or rqt.form.get("pm") == Permission.Master.value:
                    return json("您没有相关权限")

                if rqt.form.get("password"):
                    validate_password(rqt.form.get('password'))
                    hash_password = rqt.app.shared_ctx.password_hasher.hash(rqt.form.get("password"))
                else:
                    hash_password = None
                await User.create(uid=user_info.user_id,
                                  tuid=user_info.tieba_uid,
                                  username=user_info.user_name,
                                  password=hash_password,
                                  master=user.uid)
            else:
                if permission.permission == Permission.Master.value or rqt.form.get("pm") == Permission.Master.value:
                    return json("您没有相关权限")

            permission.permission = rqt.form.get("pm")
            await permission.save()

            await ExecuteLog.create(user=user.username,
                                    type=ExecuteType.PermissionEdit,
                                    obj=user_info.user_name,
                                    note=f"设置[{user_info.user_name}]为 {permission.permission}")

            return json(data=await permission.to_dict())
        except ValueError:
            return json("没有该贴吧用户")


bp_manager.add_route(UserPermission.as_view(), "/user_pm")
