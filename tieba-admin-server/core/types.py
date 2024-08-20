from types import SimpleNamespace
from typing import Type, Dict, List

from argon2 import PasswordHasher
from sanic import Sanic, Config, Request

from core.plugin.plugin import PluginManager
from core.setting import ConfigManager


class Context:
    config: ConfigManager
    plugin_manager: PluginManager
    password_hasher: PasswordHasher
    db_config: Dict
    tb_client: List


TBApp: Type[Sanic[Config, Context]] = Sanic[Config, Context]


class TBRequest(Request[TBApp, SimpleNamespace]):
    app: TBApp
