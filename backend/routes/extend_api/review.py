from pydantic import BaseModel
from sanic import Blueprint

from core.types import TBRequest
from core.utils import json
from extend.review import Reviewer

bp_review = Blueprint("review", url_prefix="/review")


class BotStatus(BaseModel):
    name: str
    status: bool


@bp_review.post("/bot/status/<action>")
async def bot_actions(rqt: TBRequest, action: str):
    match action:
        case "get":
            task = rqt.app.get_task(name="review", raise_exception=False)
            if task is None:
                status = False
            else:
                status = True
            return json(data=BotStatus(name="review", status=status).dict())
        case "start":
            reviewer = Reviewer(rqt.app)
            _ = rqt.app.add_task(reviewer.start(), name="review")
            return json(data=BotStatus(name="review", status=True).dict())
        case "stop":
            task = rqt.app.get_task(name="review", raise_exception=False)
            task.cancel()
            return json(data=BotStatus(name="review", status=False).dict())
        case _:
            return json("未知操作")
