import asyncio
import random
from asyncio import sleep
from typing import List

from aiotieba import Client, PostSortType, logging
from aiotieba.typing import Threads, Thread, Posts, Post, Comments, Comment
from sanic.log import logger
from tortoise import Tortoise, connections, ConfigurationError

from core.enum import Permission
from core.models import ForumUserPermission, User, Config
from core.plugin.plugin import BasePlugin
from . import execute
from .checker import CheckMap, manager
from .models import Forum as RForum
from .models import Function as RFunction
from .models import Post as RPost
from .models import Thread as RThread


class Reviewer(BasePlugin):
    """
    继承自Plugin基类
    """
    PLUGIN_MODEL = "plugins.review.models"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.check_map: CheckMap = manager.check_map
        self.FUP: ForumUserPermission = None
        self.no_exec = True
        self.check_name_map = manager.check_name_map
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
            executor = execute.Executor(client=client, obj=ce_thread)

            async def get_execute(_check):
                func_enable = await RFunction.get(function=_check['function'].__name__)
                if not func_enable.enable:
                    return None
                _executor = await _check['function'](ce_thread, client)
                if not _executor:
                    raise TypeError("Need to return Executor object")
                executor.exec_compare(_executor)

            await asyncio.gather(*[get_execute(check) for check in self.check_map['thread']])

            if not self.no_exec:
                await executor.run()
            else:
                logger.debug(f"[review] [Thread] {executor}")

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
                need_next_check.append(clt_thread)
                await check_and_execute(clt_thread)
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
            executor = execute.Executor(client=client, obj=ce_post)

            async def get_execute(_check):
                func_enable = await RFunction.get(function=_check['function'].__name__)
                if not func_enable.enable:
                    return None
                _executor = await _check['function'](ce_post, client)
                if not _executor:
                    raise TypeError("Need to return Executor object")
                executor.exec_compare(_executor)

            await asyncio.gather(*[get_execute(check) for check in self.check_map['post']])

            if not self.no_exec:
                await executor.run()
            else:
                logger.debug(f"[review] [Post] {executor}")

        async def check_reply_num(crn_post: Post):
            prev_post = await RPost.filter(pid=crn_post.pid).get_or_none()
            if prev_post:
                if crn_post.reply_num < prev_post.reply_num:
                    await RPost.filter(pid=crn_post.pid).update(reply_num=crn_post.reply_num)
                elif crn_post.reply_num > prev_post.reply_num:
                    need_next_check.append(crn_post)
                    await RPost.filter(pid=crn_post.pid).update(reply_num=crn_post.reply_num)
            else:
                need_next_check.append(crn_post)
                await check_and_execute(crn_post)
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
            executor = execute.Executor(client=client, obj=cae_comment)

            async def get_execute(_check):
                func_enable = await RFunction.get(function=_check['function'].__name__)
                if not func_enable.enable:
                    return None
                _executor = await _check['function'](cae_comment, client)
                if not _executor:
                    raise TypeError("Need to return Executor object")
                executor.exec_compare(_executor)

            await asyncio.gather(*[get_execute(check) for check in self.check_map['comment']])

            if not self.no_exec:
                await executor.run()
            else:
                logger.debug(f"[review] [Comment] {executor}")

        async def check_comment_of_db(ccod_comment: Comment):
            prev_comment = await RPost.filter(pid=ccod_comment.pid).get_or_none()
            if not prev_comment:
                await check_and_execute(ccod_comment)
                await RPost.create(pid=ccod_comment.pid, tid=ccod_comment.tid, ppid=post.pid)

        await asyncio.gather(*[check_comment_of_db(comment) for comment in comments])

    async def run_with_client(self, user: User, min_time=35.0, max_time=60.0):
        """
        实现持续监控的关键函数
        Args:
            user: 传入了执行账号
            min_time: 最短间隔时间（单位：秒）
            max_time: 最大间隔时间（单位：秒）
        """
        while True:
            async with Client(user.BDUSS, user.STOKEN) as client:
                logger.debug(f"[Reviewer] review {self.FUP.fname}")
                rst = await RForum.get(fname=self.FUP.fname)
                if rst.enable:
                    await self.check_threads(client, self.FUP.fname)
                if self.no_exec:
                    break
            await sleep(random.uniform(min_time, max_time))

    @classmethod
    async def get_fup(cls):
        fup = await ForumUserPermission.filter(permission=Permission.Master.value).get_or_none()
        if fup:
            rf = await RForum.filter(fname=fup.fname).get_or_none()
            if not rf:
                await RForum.create(fname=fup.fname)
        return fup

    @classmethod
    async def init_plugin(cls):
        logging.set_logger(logger)

        no_exec = await Config.get_bool(key="REVIEW_NO_EXEC")
        if no_exec is None:
            await Config.set_config(key="REVIEW_NO_EXEC", v1=True)

        await cls.get_fup()

        await RFunction.filter(function__not_in=manager.check_name_map).delete()
        old_name_map: List[str] = [i.function for i in (await RFunction.all())]
        func_list = []

        for c in manager.check_name_map:
            if c not in old_name_map:
                func_list.append(RFunction(function=c))
        await RFunction.bulk_create(func_list)

    async def on_start(self):
        logging.set_logger(logger)
        await Tortoise.init(config=self.kwargs["db_config"])
        await Tortoise.generate_schemas()

        self.no_exec = await Config.get_bool(key="REVIEW_NO_EXEC")
        self.FUP = await self.get_fup()

    async def on_running(self):
        user: User = await self.FUP.user
        await asyncio.gather(self.run_with_client(user))

    async def on_stop(self):
        try:
            await connections.close_all()
        except ConfigurationError:
            pass
        except AttributeError:
            pass
