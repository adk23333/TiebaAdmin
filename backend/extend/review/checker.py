from abc import ABC, abstractmethod
from typing import Union, MutableMapping, Type

from aiotieba import Client
from aiotieba.typing import Thread, Post, Comment

from core.enum import Permission
from core.models import ForumPermission
from core.types import TBApp
from .executor import empty, delete, block

CHECKER_MAP: MutableMapping[str, Type["BaseChecker"]] = {}


class BaseChecker(ABC):
    ignore_office = True
    ignore_admin = True

    @staticmethod
    @abstractmethod
    def name() -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def description() -> str:
        raise NotImplementedError

    @classmethod
    async def thread(cls, thread: Thread, client: Client, app: TBApp):
        return empty()

    @classmethod
    async def post(cls, post: Post, client: Client, app: TBApp):
        return empty()

    @classmethod
    async def comment(cls, comment: Comment, client: Client, app: TBApp):
        return empty()

    def __init_subclass__(cls, **kwargs):
        CHECKER_MAP[cls.name()] = cls


class KeywordChecker(BaseChecker):

    @staticmethod
    def name() -> str:
        return "CheckKeyword"

    @staticmethod
    def description() -> str:
        return "检查关键词并处理"

    @classmethod
    async def check(cls, obj: Union[Thread, Post, Comment], app: TBApp):
        if obj.user.level <= app.ctx.config.extend.review.keyword_level:
            keywords = app.ctx.config.extend.review.keywords
            for kw in keywords:
                if obj.text.find(kw) != -1:
                    return delete(obj, note=cls.name())
        return empty()

    @classmethod
    async def thread(cls, thread: Thread, client: Client, app: TBApp):
        return await cls.check(thread, app)

    @classmethod
    async def post(cls, post: Post, client: Client, app: TBApp):
        return await cls.check(post, app)

    @classmethod
    async def comment(cls, comment: Comment, client: Client, app: TBApp):
        return await cls.check(comment, app)


class BlackChecker(BaseChecker):

    @staticmethod
    def name() -> str:
        return "CheckBlack"

    @staticmethod
    def description() -> str:
        return "检查循环封禁用户"

    @classmethod
    async def black(cls, obj: Union[Thread, Post, Comment]):
        fp = await ForumPermission.get_or_none(user_id=obj.user.user_id, forum=obj.fname)
        if fp and fp.permission == Permission.BLACK:
            return block(obj.fid, obj.user.user_id, 90, cls.name())
        return empty()

    @classmethod
    async def thread(cls, thread: Thread, client: Client, app: TBApp):
        return await cls.black(thread)

    @classmethod
    async def post(cls, post: Post, client: Client, app: TBApp):
        return await cls.black(post)

    @classmethod
    async def comment(cls, comment: Comment, client: Client, app: TBApp):
        return await cls.black(comment)


class LevelWallChecker(BaseChecker):

    @staticmethod
    def name() -> str:
        return "LevelWall"

    @staticmethod
    def description() -> str:
        return "等级墙"

    @classmethod
    async def thread(cls, thread: Thread, client: Client, app: TBApp):
        if thread.user.level <= app.ctx.config.extend.review.level_wall:
            return delete(thread, note=cls.name())
        return empty()
