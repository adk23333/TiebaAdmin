import aiotieba
import logging
from argon2 import PasswordHasher
from multiprocessing import Manager
from sanic import FileNotFound, SanicException
from sanic.log import logger
from sanic.response import file
from sanic_ext import Extend

from core.account import bp_account
from core.exception import ArgException, FirstLoginError
from core.jwt import init_jwt
from core.log import bp_log
from core.manager import bp_manager
from core.models import init_database
from core.plugin.buleprint import bp_plugin
from core.plugin.plugin import PluginManager
from core.setting import server_config
from core.types import TBApp, TBRequest
from core.utils import json

app = TBApp("tieba-admin-server")
Extend(app)

app.ctx.config = server_config
if not app.ctx.config.load():
    app.ctx.config.dump()

if app.ctx.config["server"]["dev"]:
    logger.setLevel(logging.DEBUG)
aiotieba.logging.set_logger(logger)

init_jwt(app)

app.blueprint(bp_manager)
app.blueprint(bp_log)
app.blueprint(bp_account)
app.blueprint(bp_plugin)


@app.main_process_ready
async def ready(_app: TBApp):
    _app.shared_ctx.plugins = Manager().list()


@app.before_server_start
async def init_server(_app: TBApp):
    _app.ctx.password_hasher = PasswordHasher()
    _app.ctx.plugin_manager = PluginManager(_app)
    await init_database(_app)


@app.on_request
async def first_login_check(rqt: TBRequest):
    is_first = rqt.app.ctx.config["first_start"]
    if is_first and rqt.path != '/api/auth/first_login' and rqt.path.startswith("/api"):
        raise FirstLoginError(is_first)


@app.exception(FileNotFound, ArgException, FirstLoginError)
async def exception_handle(rqt: TBRequest, e: SanicException):
    if isinstance(e, FileNotFound):
        return await file("./web/index.html", status=404)
    elif isinstance(e, ArgException):
        return json(e.message, status_code=e.status_code)
    elif isinstance(e, FirstLoginError):
        is_first = e.is_first
        if is_first is None:
            is_first = True
        return json(e.message, {"is_first": is_first}, 403)


if app.ctx.config["server"]["web"]:
    app.static("/", "./web/", index="index.html")

if __name__ == "__main__":
    app.run(
        host=app.ctx.config["server"]["host"],
        port=app.ctx.config["server"]["port"],
        dev=app.ctx.config["server"]["dev"],
        workers=app.ctx.config["server"]["workers"],
    )
