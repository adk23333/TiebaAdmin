import asyncio
from abc import ABCMeta, abstractmethod
from typing import MutableMapping, Type

from sanic import Sanic
from sanic.log import logger

from core.setting import ConfigManager


class BasePlugin(object):
    """
    插件基类，定义了一个插件应该有的属性及方法
    """
    PLUGIN_MODEL = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @classmethod
    async def init_plugin(cls):
        ...

    async def on_start(self):
        ...

    async def on_running(self):
        ...

    async def on_stop(self):
        ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_tb:
            logger.warning(f"[{self.__class__.__name__}] {exc_type}: {exc_val}")
        await self.on_stop()
        logger.info(f"[{self.__class__.__name__}] stopped.")

    @classmethod
    async def _start_plugin_with_process(cls, **kwargs):
        async with cls(**kwargs) as plugin:
            await plugin.on_start()
            await plugin.on_running()

    @classmethod
    def start_plugin_with_process(cls, **kwargs):
        try:
            logger.setLevel(kwargs["log_level"])
            logger.info(f"[{cls.__name__}] running.")
            asyncio.run(cls._start_plugin_with_process(**kwargs))
        except Exception:
            pass
        except KeyboardInterrupt:
            pass


class Plugin(metaclass=ABCMeta):
    name: str = None
    package_name: str = None
    config_path: str = f"plugins/{package_name}/config.toml"
    config: ConfigManager = None

    def __init__(self, app: Sanic):
        self._app = app

        if self.name is None:
            self.name = self.package_name

        if isinstance(self.config, ConfigManager):
            if not self.config.load():
                self.config.dump()

    def __init_subclass__(cls, **kwargs):
        if cls.package_name is None:
            raise NotImplementedError(f"请给 {cls} 定义插件的包名")
        PluginManager.plugins[cls.package_name] = cls

    @abstractmethod
    async def running(self):
        raise NotImplementedError

    async def after_running(self):
        ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.after_running()
        self._app.shared_ctx.plugins.remove(f"p-{self.package_name}")
        if exc_val is not None:
            logger.error(f"plugin: <{self.package_name}> ", exc_val)

    @classmethod
    async def task(cls, app: Sanic):
        async with cls(app) as plugin:
            logger.info(f"plugin: <{plugin.package_name}> running.")
            await plugin.running()
            logger.info(f"plugin: <{plugin.package_name}> stopped.")


class PluginManager:
    plugins: MutableMapping[str, Type[Plugin]] = {}

    def __init__(self, app: Sanic):
        self._app = app

    async def start_plugin(self, package: str):
        if package not in self.plugins.keys():
            raise KeyError
        pname = f"p-{package}"
        if pname not in self._app.shared_ctx.plugins:
            self._app.shared_ctx.plugins.append(pname)
            _ = self._app.add_task(
                self.plugins[package].task(self._app),
                name=pname
            )

    async def stop_plugin(self, package: str, msg: str = None):
        pname = f"p-{package}"
        await self._app.cancel_task(pname, msg)
