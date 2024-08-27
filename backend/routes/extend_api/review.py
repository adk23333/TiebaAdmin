from pydantic import BaseModel
from sanic import Blueprint

from core.types import TBRequest
from core.utils import json
from extend.review import Reviewer, ReviewForum

bp_review = Blueprint("review", url_prefix="/review")


@bp_review.get("/config")
async def get_config(rqt: TBRequest):
    return json(data=rqt.app.ctx.config.extend.review.dict())


class BotStatus(BaseModel):
    name: str
    status: bool


def get_bot_status(rqt: TBRequest):
    task = rqt.app.get_task(name="review", raise_exception=False)
    if task is None:
        return False
    elif task.done():
        return False
    else:
        return True


@bp_review.post("/bot/status/<action>")
async def bot_actions(rqt: TBRequest, action: str):
    match action:
        case "get":
            return json(data=BotStatus(name="review", status=get_bot_status(rqt)).dict())
        case "start":
            reviewer = Reviewer(rqt.app)
            _ = rqt.app.add_task(reviewer.start(), name="review")
            return json(data=BotStatus(name="review", status=get_bot_status(rqt)).dict())
        case "stop":
            await rqt.app.cancel_task(name="review", raise_exception=False)
            return json(data=BotStatus(name="review", status=get_bot_status(rqt)).dict())
        case _:
            return json("未知操作")


@bp_review.post("/dev/<action>")
async def dev_actions(rqt: TBRequest, action: str):
    match action:
        case "get":
            return json(data=rqt.app.ctx.config.extend.review.dev)
        case "update":
            if rqt.form.get("dev", 1) == "1":
                rqt.app.ctx.config.extend.review.dev = True
            else:
                rqt.app.ctx.config.extend.review.dev = False
            rqt.app.ctx.config.dump()
            return json(data=rqt.app.ctx.config.extend.review.dev)
        case _:
            return json("未知操作")


@bp_review.post("/keyword/<action>")
async def keyword_actions(rqt: TBRequest, action: str):
    match action:
        case "get":
            return json(data=rqt.app.ctx.config.extend.review.keywords)
        case "update":
            data = rqt.json
            if isinstance(data, list):
                rqt.app.ctx.config.extend.review.keywords = data
                rqt.app.ctx.config.dump()
                return json(data=rqt.app.ctx.config.extend.review.keywords)
            else:
                return json("请按正确的格式上传关键词")
        case _:
            return json("未知操作")


@bp_review.post("/forum/<action>")
async def forum_action(rqt: TBRequest, action: str):
    match action:
        case "get":
            return json(data=rqt.app.ctx.config.extend.review.forums)
        case "update":
            data = rqt.json
            if isinstance(data, list):
                rqt.app.ctx.config.extend.review.forums = [ReviewForum(**i) for i in data]
                rqt.app.ctx.config.dump()
                return json(data=rqt.app.ctx.config.extend.review.dict()["forums"])
            else:
                return json("请按正确的格式上传贴吧列表")
        case _:
            return json("未知操作")
