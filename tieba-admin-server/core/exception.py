from sanic import SanicException


class TiebaAdminException(SanicException):
    status_code = 500
    message = "贴吧管理器错误"

    def __init__(self, message=None):
        if message:
            self.message = message


class ArgException(TiebaAdminException):
    status_code = 400
    message = "参数错误"


class FirstLoginError(TiebaAdminException):
    status_code = 403
    message = "第一次登录错误"

    def __init__(self, is_first):
        self.is_first = is_first
