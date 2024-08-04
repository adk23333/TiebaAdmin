import os
import sys

from sanic import Blueprint, Request
from sanic.log import LOGGING_CONFIG_DEFAULTS
from sanic_jwt import protected, scoped

from core.exception import ArgException
from core.models import Permission, ExecuteLog
from core.utils import json

LOG_PATH = "./log"
LOGFILE = "server.log"

if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

LOG_FILE_PATH = f"{LOG_PATH}/{LOGFILE}"
LOGGING_CONFIG = LOGGING_CONFIG_DEFAULTS.copy()
LOGGING_CONFIG.update({
    "handlers": {
        "console": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "generic",
            "filename": LOG_FILE_PATH,
            'encoding': "utf-8",
            'maxBytes': 1024 * 1024 * 1,
            'backupCount': 10,
        },
        "error_console": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "generic",
            "filename": LOG_FILE_PATH,
            'encoding': "utf-8",
            'maxBytes': 1024 * 1024 * 1,
            'backupCount': 10,
        },
        "access_console": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stdout,
        },
    },
})

bp_log = Blueprint("log", url_prefix="/api/logs")


@bp_log.get("/exec")
@protected()
@scoped(Permission.min(), False)
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
