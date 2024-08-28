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


class ExecutorNotFoundError(TiebaAdminException):
    status_code = 404
    message = "没有发现可用执行者账户"


class Unauthorized(TiebaAdminException):
    status_code = 401
    message = "权限不足"
