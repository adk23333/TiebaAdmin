from pydantic import BaseModel
from sanic import Blueprint
from sanic_jwt import scoped

from core.enum import Permission
from core.types import TBRequest
from core.utils import json
from extend.command.handle import CommandHandle

bp_command = Blueprint("command", url_prefix="/command")


@bp_command.get("/config")
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_config(rqt: TBRequest):
    return json(data=rqt.app.ctx.config.extend.command.dict())


class BotStatus(BaseModel):
    name: str
    status: bool


def get_bot_status(rqt: TBRequest):
    task = rqt.app.get_task(name="command", raise_exception=False)
    if task is None:
        return False
    elif task.done():
        return False
    else:
        return True


@bp_command.post("/bot/status/<action>")
@scoped(Permission.GE_HIGH_ADMIN.scopes, False)
async def bot_actions(rqt: TBRequest, action: str):
    status = get_bot_status(rqt)
    match action:
        case "get":
            return json(data=BotStatus(name="command", status=status).dict())
        case "start":
            if not status:
                command = CommandHandle(rqt.app)
                _ = rqt.app.add_task(command.start(), name="command")
            return json(data=BotStatus(name="command", status=status).dict())
        case "stop":
            if status:
                await rqt.app.cancel_task(name="command", raise_exception=False)
            return json(data=BotStatus(name="command", status=status).dict())
        case _:
            return json("未知操作")
