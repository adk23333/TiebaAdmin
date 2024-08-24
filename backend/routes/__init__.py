from sanic import Blueprint

from .account import bp_account
from .extend_api import bpg_extend
from .log import bp_log
from .manager import bp_manager

api_group = Blueprint.group(
    bpg_extend,
    bp_account,
    bp_log,
    bp_manager,
    url_prefix="/api"
)
