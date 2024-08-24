from sanic import Blueprint, Request
from sanic_jwt import scoped

from core.enum import Permission
from core.exception import ArgException
from core.models import ExecuteLog
from core.utils import json

bp_log = Blueprint("log", url_prefix="/api/logs")


@bp_log.get("/exec")
@scoped(Permission.GE_MIN_ADMIN.scopes, False)
async def get_log(rqt: Request):
    try:
        limit = int(rqt.args.get("limit", 20))

        if limit > 50 or limit <= 0:
            limit = 50
        pn = int(rqt.args.get("pn", 1))
        if pn < 1:
            pn = 1
    except (TypeError, ValueError):
        raise ArgException
    offset = (pn - 1) * limit
    logs = await ExecuteLog.all().offset(offset).limit(limit)
    return json(data={"items": [await log.to_dict() for log in logs], "total": await ExecuteLog.all().count()})
