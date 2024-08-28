import base64
from typing import Dict

from sanic import Request
from sanic_jwt import Configuration, Responses, exceptions, Initialize, Authentication
from sanic_jwt.exceptions import AuthenticationFailed

from .enum import Permission
from .exception import Unauthorized
from .models import User, ForumPermission
from .types import TBApp
from .utils import json


def init_jwt(app: TBApp):
    class JwtConfig(Configuration):
        url_prefix = "/api/account"
        path_to_authenticate = "/login"
        path_to_retrieve_user = "/self"
        expiration_delta = 60 * 60
        secret = app.ctx.config.server.secret
        cookie_set = True
        cookie_strict = True
        cookie_max_age = 60 * 10
        user_id = "user_id"

    class JwtResponse(Responses):
        @staticmethod
        def exception_response(rqt: Request, exception: exceptions):
            msg = str(exception)
            if exception.status_code == 500:
                msg = str(exception)
            elif isinstance(exception, exceptions.AuthenticationFailed):
                msg = str(exception)
            elif isinstance(exception, exceptions.Unauthorized):
                msg = Unauthorized.message
            else:
                if "expired" in msg:
                    msg = "授权已失效，请重新登录！"
                else:
                    msg = "未授权，请先登录！"
            return json(msg, None, exception.status_code)

    class JwtAuthentication(Authentication):
        async def authenticate(self, *args, **kwargs):
            rqt: Request = args[0]
            if rqt.headers.get("Authorization"):
                try:
                    authorization_type, credentials = rqt.headers.get("Authorization").split()
                except ValueError:
                    raise AuthenticationFailed("请先登录账号")
                if authorization_type == "Basic":
                    uid, password = (
                        base64.b64decode(credentials).decode().split(":")
                    )
                else:
                    raise AuthenticationFailed("错误的凭证")
            else:
                raise AuthenticationFailed("请先登录账号")
            try:
                user = await User.get_via_uid(uid)
                await user.verify_password(rqt.app.ctx.password_hasher, password)

                return user
            except ValueError:
                raise AuthenticationFailed("请使用UID登录")

        async def retrieve_user(self, *args, **kwargs):
            rqt: Request = args[0]
            payload: Dict = args[1]
            try:
                user_id = payload.get('user_id', None)
                user = await User.filter(user_id=user_id).get()
                return user
            except AttributeError:
                pass
            except Exception:
                raise

        async def add_scopes_to_payload(self, user: User, *args, **kwargs):
            return []

        async def extract_scopes(self, request: Request):
            payload = await self.extract_payload(request)
            if not payload:
                return None

            scopes_attribute = self.config.scopes_name()
            scopes = payload.get(scopes_attribute, None)
            if scopes is None:
                forum = request.cookies.get("forum", "变嫁")
                user_id = await self.extract_user_id(request)
                fp = await ForumPermission.get_or_none(user_id=user_id, forum=forum)
                if fp is not None:
                    scopes = Permission(fp.permission).scopes
            return scopes

    Initialize(app, configuration_class=JwtConfig,
               responses_class=JwtResponse,
               authentication_class=JwtAuthentication, )
