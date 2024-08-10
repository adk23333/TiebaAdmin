import dataclasses
import logging
import os
import signal
from asyncio import sleep

import aiotieba
from argon2 import PasswordHasher
from sanic import Sanic, Request, FileNotFound, SanicException
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
from core.schema import SchemaManager, default_schema
from core.utils import get_modules, json, sqlite_database_exits


@dataclasses.dataclass
class Context:
    schema_manager: SchemaManager = None


app = Sanic("tieba-admin-server", ctx=Context)
Extend(app)

app.ctx.schema_manager = SchemaManager("./config.yml")
app.ctx.schema_manager.load()
if app.ctx.schema_manager.schema is None:
    app.ctx.schema_manager.load(default_schema)

if app.ctx.schema_manager.schema["server"]["dev"].value:
    logger.setLevel(logging.DEBUG)
aiotieba.logging.set_logger(logger)

if not os.path.exists(app.ctx.schema_manager.schema["cache_path"].value):
    os.makedirs(app.ctx.schema_manager.schema["cache_path"].value)

if app.ctx.schema_manager.schema["server"]["db_url"].value.startswith("sqlite"):
    sqlite_database_exits(app.ctx.schema_manager.schema["server"]["db_url"].value)

models = ['core.models']
plugins = get_modules("./plugins")
for plugin in plugins.values():
    app.blueprint(plugin.bp)
    if plugin.Plugin.PLUGIN_MODEL:
        models.append(plugin.Plugin.PLUGIN_MODEL)

app.ctx.DB_CONFIG = {
    'connections': {
        'default': app.ctx.schema_manager.schema["server"]["db_url"].value
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


@app.before_server_start
async def init_server(_app: Sanic):
    for _plugin in plugins.values():
        await _plugin.Plugin.init_plugin()
    _app.ctx.password_hasher = PasswordHasher()


@app.on_request
async def first_login_check(rqt: Request):
    is_first = rqt.app.ctx.schema_manager.schema["first_start"].value
    if is_first and rqt.path != '/api/auth/first_login' and rqt.path.startswith("/api"):
        raise FirstLoginError(is_first)


@app.get("/api/plugins")
@protected()
@scoped(Permission.min(), False)
async def get_plugins(rqt: Request):
    """获取所有插件的名字

    """
    return json(data=list(plugins.keys()))


class PluginsStatus(HTTPMethodView):
    @protected()
    @scoped(Permission.min(), False)
    async def get(self, rqt: Request):
        """获取插件状态

        """
        _plugin = rqt.args.get("plugin")
        if _plugin not in plugins.keys():
            return json("插件不存在", {"status": False})
        plugin_work: dict = rqt.app.m.workers.get(f"Sanic-{_plugin}-0")
        return json("插件状态", {"status": bool(plugin_work)})

    @protected()
    @scoped(Permission.high(), False)
    async def post(self, rqt: Request):
        """设置插件状态

        """
        status = rqt.form.get("status")
        _plugin = rqt.form.get("plugin")
        if _plugin not in plugins.keys():
            return json("插件不存在", {"status": False})
        plugin_work = rqt.app.m.workers.get(f"Sanic-{_plugin}-0", None)
        if status == "1" and plugin_work:
            return json("插件已在运行", {"status": True})
        elif status == "1" and not plugin_work:
            rqt.app.m.manage(_plugin, plugins[_plugin].Plugin.start_plugin_with_process,
                             {
                                 "db_config": rqt.app.ctx.DB_CONFIG,
                                 "log_level": logger.level,
                             })
            await sleep(1)
            plugin_work: dict = rqt.app.m.workers.get(f"Sanic-{_plugin}-0")
            plugin_work.pop("start_at")
            plugin_work["status"] = True
            return json("已启动插件", plugin_work)
        elif status == "0" and plugin_work:
            os.kill(plugin_work["pid"], signal.SIGINT)
            return json("已停止插件", {"status": False})
        elif status == "0" and not plugin_work:
            return json("插件未运行", {"status": False})
        elif status is None:
            return json("插件状态", {"status": bool(plugin_work)})
        else:
            return json("参数错误")


app.add_route(PluginsStatus.as_view(), "/api/plugins/status")


@app.exception(FileNotFound, ArgException, FirstLoginError)
async def exception_handle(rqt: Request, e: SanicException):
    if isinstance(e, FileNotFound):
        return await file("./web/index.html", status=404)
    elif isinstance(e, ArgException):
        return json(e.message, status_code=e.status_code)
    elif isinstance(e, FirstLoginError):
        is_first = e.is_first
        if is_first is None:
            is_first = True
        return json(e.message, {"is_first": is_first}, 403)


if app.ctx.schema_manager.schema["server"]["web"].value:
    app.static("/", "./web/", index="index.html")

if __name__ == "__main__":
    app.run(
        host=app.ctx.schema_manager.schema["server"]["host"].value,
        port=app.ctx.schema_manager.schema["server"]["port"].value,
        dev=app.ctx.schema_manager.schema["server"]["dev"].value,
        workers=app.ctx.schema_manager.schema["server"]["workers"].value,
    )
