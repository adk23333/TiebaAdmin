import logging
import os
from multiprocessing import Manager

import aiotieba
from argon2 import PasswordHasher
from sanic import FileNotFound, SanicException
from sanic.log import logger
from sanic.response import file
from sanic.views import HTTPMethodView
from sanic_ext import Extend
from sanic_jwt import protected, scoped
from tortoise.contrib.sanic import register_tortoise

from core.account import bp_account
from core.exception import ArgException, FirstLoginError
from core.jwt import init_jwt
from core.log import bp_log
from core.manager import bp_manager
from core.models import Permission
from core.plugin import PluginManager
from core.setting import server_config
from core.types import TBApp, TBRequest
from core.utils import json, sqlite_database_exits

app = TBApp("tieba-admin-server")
Extend(app)

app.ctx.config = server_config
if not app.ctx.config.load():
    app.ctx.config.dump()

if app.ctx.config["server"]["dev"]:
    logger.setLevel(logging.DEBUG)
aiotieba.logging.set_logger(logger)

if not os.path.exists(app.ctx.config["cache_path"]):
    os.makedirs(app.ctx.config["cache_path"])

if app.ctx.config["server"]["db_url"].startswith("sqlite"):
    sqlite_database_exits(app.ctx.config["server"]["db_url"])

models = ['core.models']

app.ctx.DB_CONFIG = {
    'connections': {
        'default': app.ctx.config["server"]["db_url"]
    },
    'apps': {
        'models': {
            "models": models,
            'default_connection': 'default',
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}

register_tortoise(app, config=app.ctx.DB_CONFIG, generate_schemas=True)

init_jwt(app)

app.blueprint(bp_manager)
app.blueprint(bp_log)
app.blueprint(bp_account)


@app.main_process_ready
async def ready(_app: TBApp):
    _app.shared_ctx.plugins = Manager().list()


@app.before_server_start
async def init_server(_app: TBApp):
    _app.ctx.password_hasher = PasswordHasher()

    _app.ctx.plugin_manager = PluginManager(_app)


@app.on_request
async def first_login_check(rqt: TBRequest):
    is_first = rqt.app.ctx.config["first_start"]
    if is_first and rqt.path != '/api/auth/first_login' and rqt.path.startswith("/api"):
        raise FirstLoginError(is_first)


@app.get("/api/plugins")
@protected()
@scoped(Permission.min(), False)
async def get_plugins(rqt: TBRequest):
    """获取所有插件的名字

    """
    plugins = []
    for plugin in rqt.app.ctx.plugin_manager.plugins:
        if plugin in rqt.app.shared_ctx.plugins:
            plugins.append({"name": plugin, "status": True})
        else:
            plugins.append({"name": plugin, "status": False})
    return json(data=plugins)


class PluginsStatus(HTTPMethodView):
    @protected()
    @scoped(Permission.min(), False)
    async def get(self, rqt: TBRequest):
        """获取插件状态

        """
        _plugin = rqt.args.get("plugin")
        if _plugin not in rqt.app.ctx.plugin_manager.plugins:
            return json("插件不存在")

        if f"p-{_plugin}" in rqt.app.shared_ctx.plugins:
            return json(data={"name": _plugin, "status": True})
        else:
            return json(data={"name": _plugin, "status": False})

    @protected()
    @scoped(Permission.high(), False)
    async def post(self, rqt: TBRequest):
        """设置插件状态

        """
        _status = rqt.form.get("status")
        _plugin = rqt.form.get("plugin")
        if _plugin not in rqt.app.ctx.plugin_manager.plugins:
            return json("插件不存在")

        if f"p-{_plugin}" in rqt.app.shared_ctx.plugins:
            status = True
        else:
            status = False

        if _status == "1" and status:
            return json("插件已在运行", {"name": _plugin, "status": status})
        elif _status == "1" and not status:
            await rqt.app.ctx.plugin_manager.start_plugin(_plugin)
            return json("已启动插件", {"name": _plugin, "status": status})
        elif _status == "0" and status:
            await rqt.app.ctx.plugin_manager.stop_plugin(_plugin)
            return json("已停止插件", {"name": _plugin, "status": status})
        elif _status == "0" and not status:
            return json("插件未运行", {"name": _plugin, "status": status})
        elif _status is None:
            return json("插件状态", {"name": _plugin, "status": status})
        else:
            return json("参数错误")


app.add_route(PluginsStatus.as_view(), "/api/plugins/status")


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
