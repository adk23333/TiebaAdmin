import asyncio
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Type

from aiotieba import Client
from aiotieba.api.get_ats import At
from aiotieba.api.get_comments import Comments
from aiotieba.api.get_posts import Posts
from pydantic import BaseModel
from sanic.log import logger

from core.enum import Permission
from extend.review.executor import Executor, empty, delete, set_permission

COMMAND_MAP: Dict[str, Type["BaseCommand"]] = {}


class BaseCommand(BaseModel, ABC):
    cmd_args: Tuple[str, ...]

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
    async def handle_function(self,
                              at: At,
                              listener: Client,
                              executor: Client,
                              parent=None) -> Executor:
        raise NotImplementedError

    @staticmethod
    async def get_parent(at: At, listener: Client):
        if at.is_comment:
            await asyncio.sleep(3.0)
            comments: Comments = await listener.get_comments(at.tid, at.pid, is_comment=True)
            return comments.post

        elif at.is_thread:
            await asyncio.sleep(3.0)
            posts: Posts = await listener.get_posts(at.tid, rn=0)
            return posts.thread

        else:
            await asyncio.sleep(2.0)
            posts: Posts = await listener.get_posts(at.tid, rn=0)
            return posts.thread


class PingCommand(BaseCommand):
    msg: str = None

    @staticmethod
    def command() -> str:
        return "ping"

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_MIN_ADMIN

    async def handle_function(self, *args) -> Executor:
        logger.info(f"[Command] <ping> msg: {self.msg}")
        return empty()


class DeleteCommand(BaseCommand):
    @staticmethod
    def command() -> str:
        return "删除"

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_MIN_ADMIN

    async def handle_function(self,
                              at: At,
                              listener: Client,
                              executor: Client,
                              parent=None) -> Executor:
        if parent is None:
            parent = await self.get_parent(at, listener)
        return delete(parent, note=self.command())


class DeleteBlockCommand(BaseCommand):
    day: int = 1

    @staticmethod
    def command() -> str:
        return "删封"

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_MIN_ADMIN

    async def handle_function(self,
                              at: At,
                              listener: Client,
                              executor: Client,
                              parent=None) -> Executor:
        if parent is None:
            parent = await self.get_parent(at, listener)
        return delete(parent, self.day, self.command())


class PermissionCommand(BaseCommand):
    set_pm: str
    user: str

    @staticmethod
    def command() -> str:
        return '权限'

    @staticmethod
    def permission() -> Permission:
        return Permission.GE_SUPER_ADMIN

    async def handle_function(self,
                              at: At,
                              listener: Client,
                              executor: Client,
                              parent=None) -> Executor:
        permission = Permission.convert_zh(self.set_pm)
        if not permission:
            return empty()
        if permission == Permission.MASTER:
            return empty()
        return set_permission(at.fname, self.user, permission, self.set_pm)
