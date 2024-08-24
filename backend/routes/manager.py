from sanic import Blueprint, Request
from sanic.views import HTTPMethodView
from sanic_jwt import scoped, inject_user

from core.enum import Permission
from core.models import User
from core.utils import json

bp_manager = Blueprint("manager", url_prefix="/api/manager")


class UserPermission(HTTPMethodView):
    @scoped(Permission.GE_MIN_ADMIN.scopes, False)
    async def get(self, rqt: Request):
        users = await User.all()
        users_dict = [user.to_json() for user in users]
        return json(data=users_dict)

    @inject_user()
    @scoped(Permission.GE_SUPER_ADMIN.scopes, False)
    async def post(self, rqt: Request, user: User):
        pass


bp_manager.add_route(UserPermission.as_view(), "/user_pm")
