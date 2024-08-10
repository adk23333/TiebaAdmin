import base64

from sanic import Request, Sanic
from sanic_jwt import Configuration, Responses, exceptions, Initialize
from sanic_jwt.exceptions import AuthenticationFailed

from .models import User, ForumUserPermission
from .utils import json


def init_jwt(app: Sanic):
    async def authenticate(rqt: Request):
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
            user = await User.get_via_uid(int(uid))
            await user.verify_password(rqt.app.ctx.password_hasher, password)
            return user
        except ValueError:
            raise AuthenticationFailed("请使用uid登录")

    async def retrieve_user(rqt: Request, payload):
        try:
            uid = payload.get('uid', None)
            user = await User.filter(uid=uid).get()
            return user
        except AttributeError:
            pass
        except Exception:
            raise

    class JwtConfig(Configuration):
        url_prefix = "/api/auth"
        path_to_retrieve_user = "/self"
        expiration_delta = 60 * 60
        secret = app.ctx.schema_manager.schema["server"]["secret"].value
        # cookie_set = True
        # cookie_access_token_name = "token"
        user_id = "uid"

    class JwtResponse(Responses):
        @staticmethod
        def exception_response(rqt: Request, exception: exceptions):
            msg = str(exception)
            if exception.status_code == 500:
                msg = str(exception)
            elif isinstance(exception, exceptions.AuthenticationFailed):
                msg = str(exception)
            elif isinstance(exception, exceptions.Unauthorized):
                msg = "您没有访问该接口的权限"
            else:
                if "expired" in msg:
                    msg = "授权已失效，请重新登录！"
                else:
                    msg = "未授权，请先登录！"
            return json(msg, None, exception.status_code)

    async def scope_extender(user: User, *args, **kwargs):
        p = await ForumUserPermission.get(user=user)
        return p.permission

    Initialize(app, authenticate=authenticate,
               retrieve_user=retrieve_user,
               configuration_class=JwtConfig,
               responses_class=JwtResponse,
               add_scopes_to_payload=scope_extender)
