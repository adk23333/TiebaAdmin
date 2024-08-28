import logging

import aiotieba
from argon2 import PasswordHasher
from pydantic import ValidationError as PydanticValidationError
from sanic import FileNotFound, SanicException
from sanic.log import logger
from sanic.response import file
from sanic_ext import Extend
from sanic_ext.exceptions import ValidationError as SanicValidationError

from core.exception import ArgException, Unauthorized
from core.exception import ExecutorNotFoundError
from core.jwt import init_jwt
from core.models import init_database
from core.setting import config, SERVER_NAME
from core.types import TBApp, TBRequest
from core.utils import json
from routes import api_group

app = TBApp(SERVER_NAME)
Extend(app)

app.ctx.config = config
if app.ctx.config.server.dev:
    logger.setLevel(logging.DEBUG)
aiotieba.logging.set_logger(logger)

init_jwt(app)

app.blueprint(api_group)


@app.main_process_ready
async def ready(_app: TBApp):
    pass


@app.before_server_start
async def init_server(_app: TBApp):
    _app.ctx.password_hasher = PasswordHasher()
    await init_database(_app)


@app.on_request
async def first_login_check(rqt: TBRequest):
    is_first = rqt.app.ctx.config.first_start
    if is_first and rqt.path != '/api/account/login/first' and rqt.path.startswith("/api"):
        return json("尚未创建管理员账户", status_code=404)


@app.exception(
    FileNotFound,
    ArgException,
    PydanticValidationError,
    SanicValidationError,
    ExecutorNotFoundError,
)
async def exception_handle(rqt: TBRequest, e: SanicException):
    if isinstance(e, FileNotFound):
        if rqt.app.ctx.config.server.web:
            return await file("./web/index.html", status=404)
        else:
            return json("FileNotFound", status_code=404)
    elif isinstance(e, ArgException):
        return json(e.message, status_code=e.status_code)
    elif isinstance(e, (PydanticValidationError, SanicValidationError)):
        return json("参数错误")
    elif isinstance(e, ExecutorNotFoundError):
        return json(e.message, status_code=e.status_code)
    elif isinstance(e, Unauthorized):
        return json(e.message, status_code=e.status_code)


if app.ctx.config.server.web:
    app.static("/", "./web/", index="index.html")

if __name__ == "__main__":
    app.run(
        host=app.ctx.config.server.host,
        port=app.ctx.config.server.port,
        dev=app.ctx.config.server.dev,
        workers=app.ctx.config.server.workers,
    )
