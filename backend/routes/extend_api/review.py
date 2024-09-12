from pydantic import BaseModel
from sanic import Blueprint
from sanic_jwt import scoped

from core.enum import Permission
from core.types import TBRequest
from core.utils import json
from extend.review import Reviewer, ReviewConfig

bp_review = Blueprint("review", url_prefix="/review")


@bp_review.get("/config")
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
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
@scoped(Permission.GE_HIGH_ADMIN.scopes, False)
async def bot_actions(rqt: TBRequest, action: str):
    status = get_bot_status(rqt)
    match action:
        case "get":
            return json(data=BotStatus(name="review", status=status).dict())

        case "start":
            if not status:
                reviewer = Reviewer(rqt.app)
                _ = rqt.app.add_task(reviewer.start(), name="review")

        case "stop":
            if status:
                await rqt.app.cancel_task(name="review", raise_exception=False)

        case _:
            return json("未知操作")

    status = get_bot_status(rqt)
    return json(data=BotStatus(name="review", status=status).dict())


@bp_review.post("/config/<action>")
@scoped(Permission.GE_SUPER_ADMIN.scopes, False)
async def config_actions(rqt: TBRequest, action: str):
    match action:
        case "get":
            return json(data=rqt.app.ctx.config.extend.review.dict())
        case "update":
            body = ReviewConfig(**rqt.json)
            rqt.app.ctx.config.extend.review = body
            rqt.app.ctx.config.dump()
            return json(data=rqt.app.ctx.config.extend.review.dict())
        case _:
            return json("未知操作")
