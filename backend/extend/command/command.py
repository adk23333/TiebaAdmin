import asyncio
import dataclasses
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Type, Union

from aiotieba import Client
from aiotieba.api.get_ats import At
from aiotieba.api.get_comments import Comments, Post_c
from aiotieba.api.get_posts import Posts, Thread_p
from sanic.logging.loggers import logger

from core.enum import Permission
from core.models import ForumPermission
from extend.review.checker_manage import Executor, empty, delete

COMMAND_MAP: Dict[str, Type["BaseCommand"]] = {}


@dataclasses.dataclass
class BaseCommand(ABC):
    cmd_args: Tuple[str]
    at: At
    listener: Client = None
    parent: Union[Thread_p, Post_c] = None
    executor: Client = None

    @staticmethod
    @abstractmethod
    def command() -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def permission() -> Permission:
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        COMMAND_MAP[cls.command()] = cls

    @abstractmethod
    async def handle_function(self) -> Executor:
        raise NotImplementedError

    async def check_permission(self):
        fp = await ForumPermission.get_or_none(user_id=self.at.author_id, forum=self.at.fname)
        if fp is None:
            pm = Permission.ORDINARY
        else:
            pm = Permission(fp.permission)

        if pm in self.permission():
            return True
        else:
            return False

    async def get_parent(self):
        if self.parent is None:
            if self.at.is_comment:
                await asyncio.sleep(3.0)
                comments: Comments = await self.listener.get_comments(self.at.tid, self.at.pid, is_comment=True)
                self.parent = comments.post

            elif self.at.is_thread:
                await asyncio.sleep(3.0)
                posts: Posts = await self.listener.get_posts(self.at.tid, rn=0)
                self.parent = posts.thread

            else:
                await asyncio.sleep(2.0)
                posts: Posts = await self.listener.get_posts(self.at.tid, rn=0)
                self.parent = posts.thread


@dataclasses.dataclass
class PingCommand(BaseCommand):
    msg: str = None

    @staticmethod
    def command() -> str:
        return "ping"

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_MIN_ADMIN

    async def handle_function(self) -> Executor:
        logger.info(f"[Command] <ping> msg: {self.msg}")
        print(f"[Command] <ping> msg: {self.msg}")
        return empty()


@dataclasses.dataclass
class DeleteCommand(BaseCommand):
    @staticmethod
    def command() -> str:
        return "删除"

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_MIN_ADMIN

    async def handle_function(self) -> Executor:
        await self.get_parent()
        return delete(self.parent, 0, self.__class__.__name__)


@dataclasses.dataclass
class DeleteBlockCommand(BaseCommand):
    day: str = "1"

    @staticmethod
    def command() -> str:
        return "删封"

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_MIN_ADMIN

    async def handle_function(self) -> Executor:
        await self.get_parent()
        try:
            day = int(self.day)
        except ValueError:
            day = 1
        return delete(self.parent, day)
