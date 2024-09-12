import asyncio
import random
from asyncio import sleep
from typing import List, Dict, Set, Type, Optional

from aiotieba import Client, PostSortType
from aiotieba.typing import Threads, Thread, Posts, Post, Comments, Comment
from sanic.log import logger

from core.enum import Permission, ExecuteType
from core.models import ForumPermission
from core.types import TBApp
from .checker import CHECKER_MAP, BaseChecker
from .executor import Executor, OFFICES_ID
from .models import Post as RPost
from .models import Thread as RThread


class Reviewer:
    name = "review"
    sender = "BOT"

    def __init__(self, app: TBApp = None):
        self.app = app
        self.forums: List[ForumPermission] = []
        self.dev = True
        self.functions: Dict[str, Set[str]] = {}
        self.semaphore = asyncio.Semaphore(8)

    async def check_threads(self, client: Client, fname: str):
        """
        检查主题贴的内容
        Args:
            client: 传入了执行账号的贴吧客户端
            fname: 贴吧名

        """
        async with self.semaphore:
            first_threads: Threads = await client.get_threads(fname)

        need_next_check: List[Thread] = []

        async def check_and_execute(ce_thread: Thread):
            executor: Optional[Executor] = None

            async def get_execute(_check: Type[BaseChecker]):
                nonlocal executor

                if _check.name() not in self.functions.get(ce_thread.fname, ()):
                    return None

                if _check.ignore_office and ce_thread.user.user_id in OFFICES_ID:
                    return None

                fp = await ForumPermission.get_or_none(user_id=ce_thread.author_id, forum=ce_thread.fname)
                if _check.ignore_admin and fp and Permission(fp.permission) in Permission.GE_CREATOR:
                    return None

                _executor = await _check.thread(ce_thread, client, self.app)
                if not _executor:
                    raise TypeError("Need to return Executor object")
                if executor is None:
                    executor = _executor
                else:
                    executor = Executor.exec_compare(executor, _executor)

            await asyncio.gather(*[get_execute(Checker) for Checker in CHECKER_MAP.values()])

            if executor is None:
                return None

            executor.set_base_info(self.name, self.sender)
            if not self.dev:
                await executor.run(client)
            elif executor.type != ExecuteType.EMPTY:
                logger.debug(f"[{self.name}] [thread] {executor}")

            return executor

        async def check_last_time(clt_thread: Thread):
            if clt_thread.is_livepost:
                return None
            prev_thread = await RThread.filter(tid=clt_thread.tid).get_or_none()
            if prev_thread:
                if clt_thread.last_time < prev_thread.last_time:
                    await RThread.filter(tid=clt_thread.tid).update(last_time=clt_thread.last_time)
                elif clt_thread.last_time > prev_thread.last_time:
                    need_next_check.append(clt_thread)
                    await RThread.filter(tid=clt_thread.tid).update(last_time=clt_thread.last_time)
            else:
                executor = await check_and_execute(clt_thread)
                if not executor or executor.type not in ExecuteType.delete():
                    need_next_check.append(clt_thread)
                await RThread.create(tid=clt_thread.tid, fid=await client.get_fid(fname),
                                     last_time=clt_thread.last_time)

        await asyncio.gather(*[check_last_time(thread) for thread in first_threads])

        await asyncio.gather(*[self.check_posts(client, thread.tid) for thread in need_next_check])

    async def check_posts(self, client: Client, tid: int):
        """
        检查楼层内容
        Args:
            client: 传入了执行账号的贴吧客户端
            tid: 所在主题贴id
        """
        async with self.semaphore:
            last_posts: Posts = await client.get_posts(
                tid,
                pn=0xFFFF,
                sort=PostSortType.DESC,
                with_comments=True,
                comment_rn=10
            )

        if last_posts and last_posts[-1].floor != 1:
            last_floor = last_posts[0].floor
            need_rn = last_floor - len(last_posts)
            if need_rn > 0:
                post_set = set(last_posts.objs)
                rn_clamp = 30
                if need_rn <= rn_clamp:
                    async with self.semaphore:
                        first_posts = await client.get_posts(
                            tid, rn=need_rn, with_comments=True, comment_rn=10
                        )

                    post_set.update(first_posts.objs)
                else:
                    async with self.semaphore:
                        first_posts = await client.get_posts(
                            tid, rn=rn_clamp, with_comments=True, comment_rn=10
                        )

                    post_set.update(first_posts.objs)

                    async with self.semaphore:
                        hot_posts = await client.get_posts(
                            tid, sort=PostSortType.HOT, with_comments=True, comment_rn=10
                        )

                    post_set.update(hot_posts.objs)
                posts = list(post_set)
            else:
                posts = last_posts.objs
        else:
            posts = last_posts.objs

        need_next_check: List[Post] = []

        async def check_and_execute(ce_post: Post):
            executor: Optional[Executor] = None

            async def get_execute(_check: Type[BaseChecker]):
                nonlocal executor

                if _check.name() not in self.functions.get(ce_post.fname, ()):
                    return None

                if _check.ignore_office and ce_post.user.user_id in OFFICES_ID:
                    return None

                fp = await ForumPermission.get_or_none(user_id=ce_post.author_id, forum=ce_post.fname)
                if _check.ignore_admin and fp and Permission(fp.permission) in Permission.GE_CREATOR:
                    return None

                _executor = await _check.post(ce_post, client, self.app)
                if not _executor:
                    raise TypeError("Need to return Executor object")
                if executor is None:
                    executor = _executor
                else:
                    executor = Executor.exec_compare(executor, _executor)

            await asyncio.gather(*[get_execute(Checker) for Checker in CHECKER_MAP.values()])

            if executor is None:
                return None

            executor.set_base_info(self.name, self.sender)
            if not self.dev:
                await executor.run(client)
            elif executor.type != ExecuteType.EMPTY:
                logger.debug(f"[{self.name}] [post] {executor}")

            return executor

        async def check_reply_num(crn_post: Post):
            prev_post = await RPost.filter(pid=crn_post.pid).get_or_none()
            if prev_post:
                if crn_post.reply_num < prev_post.reply_num:
                    await RPost.filter(pid=crn_post.pid).update(reply_num=crn_post.reply_num)
                elif crn_post.reply_num > prev_post.reply_num:
                    need_next_check.append(crn_post)
                    await RPost.filter(pid=crn_post.pid).update(reply_num=crn_post.reply_num)
            else:
                executor = await check_and_execute(crn_post)
                if not executor or executor not in ExecuteType.delete():
                    need_next_check.append(crn_post)
                await RPost.create(pid=crn_post.pid, tid=tid, reply_num=crn_post.reply_num)

        await asyncio.gather(*[check_reply_num(post) for post in posts])

        await asyncio.gather(
            *[self.check_comment(client, post) for post in need_next_check]
        )

    async def check_comment(self, client: Client, post: Post):
        """
        检查楼中楼内容
        Args:
            client: 传入了执行账号的贴吧客户端
            post: 楼层
        """

        if post.reply_num > 10 or \
                (len(post.comments) != post.reply_num and post.reply_num <= 10):

            async with self.semaphore:
                last_comments: Comments = await client.get_comments(
                    post.tid, post.pid, pn=post.reply_num // 30 + 1
                )

            comment_set = set(post.comments)
            comment_set.update(last_comments.objs)
            comments = list(comment_set)
        else:
            comments = post.comments

        async def check_and_execute(cae_comment: Comment):
            executor: Optional[Executor] = None

            async def get_execute(_check: Type[BaseChecker]):
                nonlocal executor

                if _check.name() not in self.functions.get(cae_comment.fname, ()):
                    return None

                if _check.ignore_office and cae_comment.user.user_id in OFFICES_ID:
                    return None

                fp = await ForumPermission.get_or_none(user_id=cae_comment.author_id, forum=cae_comment.fname)
                if _check.ignore_admin and fp and Permission(fp.permission) in Permission.GE_CREATOR:
                    return None

                _executor = await _check.comment(cae_comment, client, self.app)
                if not _executor:
                    raise TypeError("Need to return Executor object")

                if executor is None:
                    executor = _executor
                else:
                    executor = Executor.exec_compare(executor, _executor)

            await asyncio.gather(*[get_execute(Checker) for Checker in CHECKER_MAP.values()])

            if executor is None:
                return None

            executor.set_base_info(self.name, self.sender)
            if not self.dev:
                await executor.run(client)
            elif executor.type != ExecuteType.EMPTY:
                logger.debug(f"[{self.name}] [comment] {executor}")

        async def check_comment_of_db(ccod_comment: Comment):
            prev_comment = await RPost.filter(pid=ccod_comment.pid).get_or_none()
            if not prev_comment:
                await check_and_execute(ccod_comment)
                await RPost.create(pid=ccod_comment.pid, tid=ccod_comment.tid, ppid=post.pid)

        await asyncio.gather(*[check_comment_of_db(comment) for comment in comments])

    async def run_with_client(self, fp: ForumPermission, min_time=35.0, max_time=60.0):
        """
        实现持续监控的关键函数
        Args:
            fp: 传入了执行账号
            min_time: 最短间隔时间（单位：秒）
            max_time: 最大间隔时间（单位：秒）
        """
        while True:
            logger.debug(f"[{self.name}] working ...")
            user = await fp.user.get()
            async with Client(user.BDUSS, user.STOKEN) as client:
                logger.debug(f"[{self.name}] review {fp.forum}")
                await self.check_threads(client, fp.forum)
            if self.dev:
                break
            await sleep(random.uniform(min_time, max_time))

    async def get_config(self):
        self.app.ctx.config = self.app.ctx.config.load()
        with self.app.ctx.config as config:
            self.dev = config.extend.review.dev

            forum_list = config.extend.review.forums
            forums: List[ForumPermission] = []
            for forum in forum_list:
                fp = await ForumPermission.get_or_none(user_id=forum.user_id, forum=forum.name)
                if fp is not None:
                    forums.append(fp)
                    self.functions[forum.name] = set(forum.functions)
                else:
                    config.extend.review.forums.remove(forum)  # 移除失效的吧

            self.forums = forums

    async def start(self):
        logger.info(f"[{self.name}] start")
        try:
            if self.app is not None:
                await self.get_config()
            await asyncio.gather(*[self.run_with_client(fp) for fp in self.forums])
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] stopped")
