from types import SimpleNamespace
from typing import Type, Dict, List, TYPE_CHECKING

from argon2 import PasswordHasher
from sanic import Sanic, Config, Request

if TYPE_CHECKING:
    from core.setting import Config


class Context:
    config: "Config"
    password_hasher: PasswordHasher
    db_config: Dict
    tb_client: List


TBApp: Type[Sanic[Config, Context]] = Sanic[Config, Context]


class TBRequest(Request[TBApp, SimpleNamespace]):
    app: TBApp
