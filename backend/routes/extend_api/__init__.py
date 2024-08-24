from sanic import Blueprint

from .review import bp_review

bpg_extend = Blueprint.group(bp_review, url_prefix="/extend")
