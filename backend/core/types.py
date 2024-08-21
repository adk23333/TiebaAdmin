from argon2 import PasswordHasher
from sanic import Sanic, Config, Request
from typing import Type, Dict, List

from core.plugin.plugin import PluginManager
from core.setting import ConfigManager
from types import SimpleNamespace


class Context:
    config: ConfigManager
    plugin_manager: PluginManager
    password_hasher: PasswordHasher
    db_config: Dict
    tb_client: List


TBApp: Type[Sanic[Config, Context]] = Sanic[Config, Context]


class TBRequest(Request[TBApp, SimpleNamespace]):
    app: TBApp
