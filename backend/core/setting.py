import tomllib
from pathlib import Path

import tomli_w
from pydantic import BaseModel, Field

from extend.review import ReviewConfig

CONFIG_FILE_PATH = "config.toml"
SERVER_NAME = "tieba-admin-server"


class ServerConfig(BaseModel):
    host: str = Field("0.0.0.0", description="监听地址", )
    port: int = Field(3100, description="监听端口", )
    workers: int = Field(1, description="工作进程数", )
    web: bool = Field(True, description="是否启动网页", )
    secret: str = Field("This is a big secret!!!", description="加密密钥", )
    db_url: str = Field("sqlite://./.cache/db.sqlite", description="数据库地址", )
    dev: bool = Field(False, description="开发模式", )


class Config(BaseModel):
    cache_path: str = Field("./.cache", description="缓存文件目录", )
    cache_file: str = Field("db.sqlite", description="缓存文件名", )
    first_start: bool = Field(True, description="第一次启动", )
    version: str = Field("2.0.0", description="版本号", )
    server: ServerConfig = Field(..., description="服务器启动项", )
    extend: 'ExtendConfig' = Field(..., description="扩展的配置", )

    @staticmethod
    def load():
        path = Path(CONFIG_FILE_PATH)
        if path.exists():
            with open(path, mode="rb") as fp:
                data = tomllib.load(fp)
            return Config(**data)
        else:
            return None

    def dump(self):
        with open(CONFIG_FILE_PATH, mode="wb", encoding="utf-8") as fp:
            tomli_w.dump(self.dict(), fp)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dump()
        if exc_val is not None:
            raise exc_val


class ExtendConfig(BaseModel):
    review: ReviewConfig = Field(description="review扩展的配置")


config = Config.load()
if not config:
    config = Config(server=ServerConfig(), extend=ExtendConfig())
    config.dump()
