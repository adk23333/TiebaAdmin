from sanic import Blueprint, Request
from sanic.views import HTTPMethodView
from sanic_jwt import protected, scoped, inject_user

from .enum import Permission
from .models import User
from .utils import json

bp_manager = Blueprint("manager", url_prefix="/api/manager")


class UserPermission(HTTPMethodView):
    @protected()
    @scoped(Permission.GE_MIN_ADMIN, False)
    async def get(self, rqt: Request):
        users = await User.all()
        users_dict = [user.to_json() for user in users]
        return json(data=users_dict)

    @inject_user()
    @protected()
    @scoped(Permission.GE_SUPER_ADMIN, False)
    async def post(self, rqt: Request, user: User):
        pass


bp_manager.add_route(UserPermission.as_view(), "/user_pm")
