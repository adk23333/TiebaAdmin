from typing import Dict

from sanic import Blueprint, Request
from sanic.views import HTTPMethodView

from core import level_protected
from core.models import Config, Permission
from core.utils import json
from .models import Keyword, Forum, Function

bp = Blueprint("review")


@bp.get("/api/review/info")
@level_protected(Permission.MinAdmin)
async def info(rqt: Request):
    return json(data={
        "status": None,
        "plugin": "review",
        "name": "内容审查",
        "desc": "开启这个插件后，将根据设定的关键词或者图片审查指定贴吧的帖子内容"
    })


class NoExec(HTTPMethodView):
    @level_protected(Permission.MinAdmin)
    async def get(self, rqt: Request):
        _no_exec = await Config.get_bool("REVIEW_NO_EXEC")
        return json(data={"REVIEW_NO_EXEC": _no_exec})

    @level_protected(Permission.HighAdmin)
    async def post(self, rqt: Request):
        _no_exec = rqt.form.get("bool")
        if _no_exec:
            match _no_exec:
                case "1":
                    await Config.set_config("REVIEW_NO_EXEC", str(True))
                case "0":
                    await Config.set_config("REVIEW_NO_EXEC", str(False))
                case _:
                    pass
        _no_exec = await Config.get_bool("REVIEW_NO_EXEC")
        return json(data={"REVIEW_NO_EXEC": _no_exec})


bp.add_route(NoExec.as_view(), "/api/review/no_exec")


class KeywordApi(HTTPMethodView):
    @level_protected(Permission.MinAdmin)
    async def get(self, rqt: Request):
        keywords = await Keyword.all()
        return json(data=[k.keyword for k in keywords])

    @level_protected(Permission.HighAdmin)
    async def post(self, rqt: Request):
        keywords = rqt.json
        if not keywords:
            keywords = await Keyword.all()
            return json(data=[k.keyword for k in keywords])

        keywords = [Keyword(keyword=k) for k in keywords]
        await Keyword.all().delete()
        keywords = await Keyword.bulk_create(keywords)
        return json(data=[k.keyword for k in keywords])


bp.add_route(KeywordApi.as_view(), "/api/review/keyword")


class ForumApi(HTTPMethodView):
    @level_protected(Permission.MinAdmin)
    async def get(self, rqt: Request):
        return json(data=[f.to_json() for f in await Forum.all()])

    @level_protected(Permission.HighAdmin)
    async def post(self, rqt: Request):
        _forums: Dict = rqt.json
        msg = None
        if _forums:
            _f = await Forum.filter(fname=_forums["fname"]).get_or_none()
            if _f:
                _f.enable = _forums["enable"]
                await _f.save()
                msg = f"修改{_forums['fname']}吧状态成功"
            else:
                return json(f"没有{_forums['fname']}吧的记录")

        return json(msg, [f.to_json() for f in await Forum.all()])


bp.add_route(ForumApi.as_view(), "/api/review/forum")


class FunctionApi(HTTPMethodView):
    @level_protected(Permission.MinAdmin)
    async def get(self, rqt: Request):
        return json(data=[await f.to_json() for f in await Function.all()])

    @level_protected(Permission.HighAdmin)
    async def post(self, rqt: Request):
        _func: Dict = rqt.json
        msg = None
        if _func:
            _f = await Function.filter(fname=_func["fname"], function=_func["function"]).get_or_none()
            if _f:
                _f.enable = _func["enable"]
                await _f.save()
                msg = f"修改{_func['fname']}吧{_func['function']}方法状态成功"
            else:
                return json(f"{_func['function']}不存在")

        return json(msg, [await f.to_json() for f in await Function.all()])


bp.add_route(FunctionApi.as_view(), "/api/review/function")