import asyncio
from typing import List, Tuple, Optional

from aiotieba import Client, PostSortType
from aiotieba.api.get_ats import Ats, At
from aiotieba.api.get_comments import Post_c
from aiotieba.api.get_posts import Thread_p
from aiotieba.typing import Comments, Posts
from sanic.logging.loggers import logger

from core.enum import Permission
from core.models import User, ForumPermission
from core.types import TBApp
from extend.command.command import BaseCommand, COMMAND_MAP


class CommandHandle:
    def __init__(self, app: TBApp = None):
        self.app = app
        self.last_exec_time = 0
        self.db_listener: Optional[User] = None
        self.listener_id = ""
        self.forums: List[str] = []

    def get_config(self):
        with self.app.ctx.config as config:
            self.listener_id = config.extend.command.listener
            self.forums = config.extend.command.forums

    async def start(self):
        if self.app is not None:
            self.get_config()

        self.db_listener = await User.get_or_none(user_id=self.listener_id)
        if self.db_listener is not None:
            while True:
                async with Client(self.db_listener.BDUSS, self.db_listener.STOKEN) as listener:
                    await self._start(listener)

                await asyncio.sleep(10)

    async def _start(self, listener: Client):
        ats: Ats = await listener.get_ats()
        ats: List[At] = [at for at in ats if at.create_time > self.last_exec_time]

        if ats:
            self.last_exec_time = ats[0].create_time

        results = await asyncio.gather(*[
            self.inject_executor(at, listener) for at in ats if at.fname in self.forums
        ], return_exceptions=False)
        for r in results:
            if isinstance(r, Exception):
                logger.warning(r)

    async def inject_executor(self, at: At, listener: Client):
        fp = await ForumPermission.get_or_none(forum=at.fname, is_executor=True)
        if fp is not None:
            user: User = await fp.user.get()
            async with Client(user.BDUSS, user.STOKEN) as executor:
                await self._catch_at(at, listener, executor)

    async def _catch_at(self, at: At, listener: Client, executor: Client):
        ctx, parent = await self.at2ctx(at, listener)
        if ctx is not None and await self.check_permission(at, ctx):
            if at.is_thread:
                await executor.del_thread(at.fname, tid=at.tid)
            else:
                await executor.del_post(at.fname, tid=at.tid, pid=at.pid)

            _exec = await ctx.handle_function(at, listener, executor, parent)
            await _exec.run(executor)

    def _parse(self, _text: str):
        prefix = f"@{self.db_listener.username} "
        if not _text.startswith(prefix):
            return None
        text = _text.removeprefix(prefix)

        _args = [arg.lstrip(' ') for arg in text.split(' ') if arg]
        if not _args:
            return None

        return _args

    async def at2ctx(self,
                     at: At,
                     listener: Client):
        parent: Optional[Thread_p | Post_c] = None
        if len(at.text.encode('utf-8')) >= 78:
            _text, parent = await self.get_full_text(at, listener)
        else:
            _text = at.text

        if _args := self._parse(_text):
            if _args[0] in COMMAND_MAP.keys():
                Context = COMMAND_MAP[_args[0]]

                kwargs = {}
                index = 1
                for key in Context.model_fields:
                    if key not in ("cmd_args", "at"):
                        try:
                            kwargs[key] = _args[index]
                        except IndexError:
                            break
                        index += 1
                kwargs.update({
                    "cmd_args": tuple(_args[index:]),
                    "at": at,
                })
                ctx: BaseCommand = Context(**kwargs)
                return ctx, parent

    async def get_full_text(self, at: At, listener: Client) -> Tuple[str, Post_c | Thread_p]:
        if at.is_comment:
            await asyncio.sleep(3.0)
            comments: Comments = await listener.get_comments(at.tid, at.pid, is_comment=True)
            for comment in comments:
                if comment.pid == at.pid:
                    return comment.text, comments.post

        elif at.is_thread:
            await asyncio.sleep(3.0)
            posts: Posts = await listener.get_posts(at.tid, rn=0)
            return posts.thread.text, posts.thread

        else:
            await asyncio.sleep(2.0)
            posts: Posts = await listener.get_posts(at.tid, pn=8192, rn=20, sort=PostSortType.DESC)
            text = ""
            for post in posts:
                if post.pid == at.pid:
                    text = post.contents.text
                    break
            posts: Posts = await listener.get_posts(at.tid, rn=0)
            return text, posts.thread

    @staticmethod
    async def check_permission(at: At, ctx: BaseCommand):
        fp = await ForumPermission.get_or_none(user_id=at.author_id, forum=at.fname)
        if fp is None:
            pm = Permission.ORDINARY
        else:
            pm = Permission(fp.permission)

        if pm in ctx.permission():
            return True
        else:
            return False
