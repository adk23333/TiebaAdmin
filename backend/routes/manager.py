from sanic import Blueprint, Request
from sanic_jwt import scoped, inject_user

from core.enum import Permission
from core.models import User
from core.utils import json

bp_manager = Blueprint("manager", url_prefix="/manager")


@bp_manager.get("/get")
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_manager(rqt: Request):
    users = await User.all()
    users_dict = [user.to_json() for user in users]
    return json(data=users_dict)


@bp_manager.post("/update")
@inject_user()
@scoped(Permission.GE_SUPER_ADMIN.scopes, False)
async def update_manager(rqt: Request, user: User):
    pass
