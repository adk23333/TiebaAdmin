import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime
from sanic.logging.loggers import logger
from sanic_jwt.exceptions import AuthenticationFailed
from tortoise import Model, fields, Tortoise, log
from tortoise.exceptions import DoesNotExist

from core.enum import Permission
from core.types import TBApp
from core.utils import sqlite_database_exits


async def init_database(app: TBApp):
    log.logger = logger

    if not os.path.exists(app.ctx.config["cache_path"]):
        os.makedirs(app.ctx.config["cache_path"])

    if app.ctx.config["server"]["db_url"].startswith("sqlite"):
        sqlite_database_exits(app.ctx.config["server"]["db_url"])

    models = ['core.models']
    for plugin in app.ctx.plugin_manager.plugins.values():
        models.append(plugin.models)

    app.ctx.db_config = {
        'connections': {
            'default': app.ctx.config["server"]["db_url"]
        },
        'apps': {
            'models': {
                "models": models,
                'default_connection': 'default',
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }

    await Tortoise.init(config=app.ctx.db_config)
    logger.info("Tortoise-ORM started.")
    await Tortoise.generate_schemas()


class BaseModel(Model):
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

    def to_json(self):
        return {k: v for k, v in self.__dict__.values() if not k.startswith("_")}


class User(BaseModel):
    """
    存储账号信息
    Attributes:
        user_id : 贴吧用户id
        UID : 贴吧用户的uid
        username : 贴吧用户username
        password : 登录本站的密码
        BDUSS :
        STOKEN :
        permission:
    """
    user_id = fields.CharField(pk=True, max_length=64)
    UID = fields.CharField(max_length=64, null=True, default=None)
    username = fields.CharField(max_length=64)

    enable_login = fields.BooleanField(default=False)
    password = fields.CharField(max_length=128, null=True, default=None)

    BDUSS = fields.CharField(max_length=200, null=True, default='')
    STOKEN = fields.CharField(max_length=80, null=True, default='')

    permissions: fields.ReverseRelation["ForumPermission"]

    class Meta:
        table = "user"

    @classmethod
    async def get_via_uid(cls, tuid: int):
        try:
            user = await cls.filter(tuid=tuid).get()
            return user
        except DoesNotExist:
            raise AuthenticationFailed("用户名或密码不正确")

    async def verify_password(self, password_hasher: PasswordHasher, password: str):
        try:
            password_hasher.verify(self.password, password)
            if password_hasher.check_needs_rehash(self.password):
                self.password = password_hasher.hash(password)
                await self.save(update_fields=["password"])
        except VerifyMismatchError:
            raise AuthenticationFailed("用户名或密码不正确")

    def to_json(self):
        data = super().to_json()
        data.pop("BDUSS")
        data.pop("STOKEN")
        data.pop("password")
        return data


class ForumPermission(BaseModel):
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="permissions", to_field="user_id"
    )
    forum = fields.CharField(max_length=64)
    permission = fields.IntField(default=Permission.ORDINARY.value)

    is_executor = fields.BooleanField(default=False)
    tb_permission = fields.IntField(default=Permission.ORDINARY.value)

    class Meta:
        unique_together = ("user", "forum")


class ExecuteLog(BaseModel):
    """
    记录所有有必要公开的操作记录

    Attributes:
        user: 执行操作的主体
        type: 操作类型
        obj: 被操作对象
        note: 备注
    """
    log_id = fields.BigIntField(pk=True)
    plugin = fields.CharField(max_length=64, default="TA")
    user = fields.CharField(64)
    type = fields.IntField()
    obj = fields.CharField(64)
    note = fields.TextField(default="")

    class Meta:
        table = "execute_log"
