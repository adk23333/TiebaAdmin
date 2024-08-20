from sanic import Blueprint
from sanic.views import HTTPMethodView
from sanic_jwt import protected, scoped

from core.enum import Permission
from core.types import TBRequest
from core.utils import json

bp_plugin = Blueprint("plugin", url_prefix="/api/plugin")


@bp_plugin.get("")
@protected()
@scoped(Permission.GE_MIN_ADMIN, False)
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
    @scoped(Permission.GE_MIN_ADMIN, False)
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
    @scoped(Permission.GE_HIGH_ADMIN, False)
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


bp_plugin.add_route(PluginsStatus.as_view(), "/api/plugins/status")
