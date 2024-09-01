from sanic import Blueprint

from .command import bp_command
from .review import bp_review

bpg_extend = Blueprint.group(
    bp_review,
    bp_command,
    url_prefix="/extend",
)
