from dataclasses import dataclass
from typing import Union

from aiotieba import Client
from aiotieba.api._classdef import UserInfo
from aiotieba.api.get_comments import Comment as Tb_Comment, Post_c
from aiotieba.api.get_posts import Post as Tb_Post, Thread_p
from aiotieba.api.get_tab_map import TabMap
from aiotieba.api.get_threads import Thread as Tb_Thread
from sanic.log import logger

from core.enum import ExecuteType, Permission
from core.models import ExecuteLog, ForumPermission, User
from core.utils import cut_string, arg2user_info

OFFICES_ID = {167570067: "贴吧吧主小管家", }

UnionTbThread = Union[Tb_Thread, Thread_p]
UnionTbPost = Union[Tb_Post, Post_c]


@dataclass
class Executor(object):
    """操作容器类

    所有操作都应该使用此类包装后统一处理.

    Attributes:
        type:
        plugin:
        sender:

        thread: 待处理的贴子.
        post:
        comment:
        user:
        fname_or_fid:

        day:
        note:

        db_log:
        std_log:
    """
    type: ExecuteType
    plugin: str = None
    sender: str = None

    thread: UnionTbThread = None
    post: UnionTbPost = None
    comment: Tb_Comment = None
    context_id: int = None
    zone: str = None
    user: str | int = None
    fname_or_fid: str | int = None
    permission: Permission = None

    day: int = None
    note: str = None

    db_log: bool = True
    std_log: bool = True

    async def run(self, client: Client = None):
        """
        执行操作
        Returns:
            None

        """
        user: UserInfo = await client.get_self_info()

        match self.type:
            case ExecuteType.EMPTY:
                await self.log(user, note=self.note)

            case ExecuteType.THREAD_HIDE:
                await client.hide_thread(self.thread.fid, self.thread.tid)
                await self.log(
                    user,
                    f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
                    f"{self.note} | {cut_string(self.thread.text, 50, '...')}"
                )
            case ExecuteType.THREAD_UN_HIDE:
                await client.unhide_thread(self.fname_or_fid, self.context_id)
                if isinstance(self.fname_or_fid, int):
                    fname = await client.get_fname(self.fname_or_fid)
                else:
                    fname = self.fname_or_fid
                await self.log(
                    user,
                    f"{fname}:{self.context_id}",
                    self.note
                )

            case ExecuteType.THREAD_DELETE:
                await self._thread_delete(client, user)
            case ExecuteType.THREAD_DELETE_BLOCK:
                await self._thread_delete(client, user)
                await self._block(client, user)
            case ExecuteType.THREAD_RECOVER:
                await client.recover_thread(self.fname_or_fid, self.context_id)
                if isinstance(self.fname_or_fid, int):
                    fname = await client.get_fname(self.fname_or_fid)
                else:
                    fname = self.fname_or_fid
                await self.log(
                    user,
                    f"{fname}:{self.context_id}",
                    self.note
                )

            case ExecuteType.THREAD_GOOD:
                await client.good(self.thread.fid, self.thread.tid, self.zone)
                await self.log(
                    user,
                    f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
                    f"{self.note} | {cut_string(self.thread.text, 50, '...')}"
                )
            case ExecuteType.THREAD_UN_GOOD:
                await client.ungood(self.fname_or_fid, self.context_id)
                if isinstance(self.fname_or_fid, int):
                    fname = await client.get_fname(self.fname_or_fid)
                else:
                    fname = self.fname_or_fid
                await self.log(
                    user,
                    f"{fname}:{self.context_id}",
                    self.note
                )
            case ExecuteType.THREAD_RECOMMEND:
                await client.recommend(self.thread.fid, self.thread.tid)
                await self.log(
                    user,
                    f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
                    f"{self.note} | {cut_string(self.thread.text, 50, '...')}"
                )
            case ExecuteType.THREAD_MOVE:
                tab_map: TabMap = await client.get_tab_map()
                tab_id = tab_map.map.get(self.zone, None)
                if tab_id is None:
                    tab_id = 0
                await client.move(self.thread.fid, self.thread.tid, to_tab_id=tab_id, from_tab_id=self.thread.tab_id)
                await self.log(
                    user,
                    f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
                    f"{self.note} | {tab_map[self.zone]} | {cut_string(self.thread.text, 50, '...')}"
                )
            case ExecuteType.THREAD_TOP:
                await client.top(self.thread.fid, self.thread.tid)
                await self.log(
                    user,
                    f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
                    f"{self.note} | {cut_string(self.thread.text, 50, '...')}"
                )
            case ExecuteType.THREAD_UN_TOP:
                await client.untop(self.thread.fid, self.thread.tid)
                await self.log(
                    user,
                    f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
                    f"{self.note} | {cut_string(self.thread.text, 50, '...')}"
                )

            case ExecuteType.POST_DELETE:
                await self._post_delete(client, user)
            case ExecuteType.POST_DELETE_BLOCK:
                await self._post_delete(client, user)
                await self._block(client, user)
            case ExecuteType.POST_RECOVER:
                await self._recover_post(client, user)

            case ExecuteType.COMMENT_DELETE:
                await self._comment_delete(client, user)
            case ExecuteType.COMMENT_DELETE_BLOCK:
                await self._comment_delete(client, user)
                await self._block(client, user)
            case ExecuteType.COMMENT_RECOVER:
                await self._recover_post(client, user)

            case ExecuteType.BLOCK:
                await self._block(client, user)
            case ExecuteType.UN_BLOCK:
                obj_user = await client.get_user_info(self.user)
                await client.unblock(self.fname_or_fid, obj_user.user_id)
                if isinstance(self.fname_or_fid, int):
                    fname = await client.get_fname(self.fname_or_fid)
                else:
                    fname = self.fname_or_fid
                await self.log(user, f"{fname}:{obj_user.show_name}", self.note)

            case ExecuteType.BLACK:
                obj_user = await client.get_user_info(self.user)
                await client.add_bawu_blacklist(self.fname_or_fid, id_=obj_user.user_id)
                if isinstance(self.fname_or_fid, int):
                    fname = await client.get_fname(self.fname_or_fid)
                else:
                    fname = self.fname_or_fid
                await self.log(user, f"{fname}:{obj_user.show_name} | {self.note}")

            case ExecuteType.UN_BLACK:
                obj_user = await client.get_user_info(self.user)
                await client.del_bawu_blacklist(self.fname_or_fid, obj_user.user_id)
                if isinstance(self.fname_or_fid, int):
                    fname = await client.get_fname(self.fname_or_fid)
                else:
                    fname = self.fname_or_fid
                await self.log(user, f"{fname}:{obj_user.show_name}", self.note)

            case ExecuteType.PERMISSION_EDIT:
                obj_user = await arg2user_info(client, self.user)
                db_user, _ = await User.get_or_create({
                    'user_id': obj_user.user_id,
                    'username': obj_user.user_name,
                    'UID': obj_user.tieba_uid,
                    'showname': obj_user.show_name,
                }, user_id=obj_user.user_id)
                fp, created = await ForumPermission.update_or_create({
                    'user_id': db_user.user_id,
                    'forum': self.fname_or_fid,
                    'permission': self.permission.value,
                }, forum=self.fname_or_fid, user_id=db_user.user_id)
                await self.log(
                    user,
                    f"{obj_user.show_name}",
                    self.note
                )

            case _:
                raise TypeError("未知操作类型")

    async def log(self, executor: UserInfo, obj: str = None, note: str = None):
        if self.sender is None:
            sender = ""
        else:
            if self.sender == executor.show_name:
                sender = ""
            else:
                sender = f"[{self.sender}]"

        if self.std_log:
            logger.info(f"[{self.plugin}] {self.type.name} {sender}{executor.show_name} {obj} {note}")

        if self.db_log:
            await ExecuteLog.create(
                plugin=self.plugin,
                user=f"{sender}{executor.show_name}",
                type=self.type.value,
                obj=obj,
                note=note,
            )

    @staticmethod
    def exec_compare(exec1, exec2):
        """

        Args:
            exec1 (Executor):
            exec2 (Executor):
        """
        _exec = Executor._exec_compare(exec1, exec2)
        if _exec is None:
            _exec = Executor._exec_compare(exec2, exec1)
            if _exec is None:
                raise TypeError("类型错误，无法比较")
            else:
                return _exec
        else:
            return _exec

    @staticmethod
    def _exec_compare(exec1, exec2) -> Union["Executor", None]:
        """

        Args:
            exec1 (Executor):
            exec2 (Executor):
        """
        if exec1.type == ExecuteType.EMPTY:
            return exec2

        elif exec1.type == ExecuteType.COMMENT_DELETE and exec2.type == ExecuteType.BLOCK:
            return Executor(
                type=ExecuteType.COMMENT_DELETE_BLOCK,
                plugin=exec1.plugin,
                sender=exec1.sender,
                comment=exec1.comment,
                day=exec2.day,
                note=f"{exec1.note} | {exec2.note}",
                db_log=exec1.db_log or exec2.db_log,
                std_log=exec1.std_log or exec2.std_log,
            )
        elif exec1.type == ExecuteType.COMMENT_DELETE and exec2.type == ExecuteType.COMMENT_DELETE_BLOCK:
            return exec2
        elif exec1.type == ExecuteType.COMMENT_DELETE and exec2.type == ExecuteType.COMMENT_DELETE:
            return exec1

        elif exec1.type == ExecuteType.POST_DELETE and exec2.type == ExecuteType.BLOCK:
            return Executor(
                type=ExecuteType.POST_DELETE_BLOCK,
                plugin=exec1.plugin,
                sender=exec1.sender,
                post=exec1.post,
                day=exec2.day,
                note=f"{exec1.note} | {exec2.note}",
                db_log=exec1.db_log or exec2.db_log,
                std_log=exec1.std_log or exec2.std_log,
            )
        elif exec1.type == ExecuteType.POST_DELETE and exec2.type == ExecuteType.POST_DELETE_BLOCK:
            return exec2
        elif exec1.type == ExecuteType.POST_DELETE and exec2.type == ExecuteType.POST_DELETE:
            return exec1

        elif exec1.type == ExecuteType.THREAD_HIDE and exec2.type == ExecuteType.THREAD_HIDE:
            return exec1
        elif exec1.type == ExecuteType.THREAD_HIDE and exec2.type == ExecuteType.THREAD_DELETE:
            return exec2
        elif exec1.type == ExecuteType.THREAD_HIDE and exec2.type == ExecuteType.THREAD_DELETE_BLOCK:
            return exec2
        elif exec1.type == ExecuteType.THREAD_HIDE and exec2.type == ExecuteType.BLOCK:
            return Executor(
                type=ExecuteType.THREAD_DELETE_BLOCK,
                plugin=exec1.plugin,
                sender=exec1.sender,
                thread=exec1.thread,
                day=exec2.day,
                note=f"{exec1.note} | {exec2.note}",
                db_log=exec1.db_log or exec2.db_log,
                std_log=exec1.std_log or exec2.std_log,
            )
        elif exec1.type == ExecuteType.THREAD_DELETE and exec2.type == ExecuteType.THREAD_HIDE:
            return exec1
        elif exec1.type == ExecuteType.THREAD_DELETE and exec2.type == ExecuteType.THREAD_DELETE:
            return exec1
        elif exec1.type == ExecuteType.THREAD_DELETE and exec2.type == ExecuteType.THREAD_DELETE_BLOCK:
            return exec2
        elif exec1.type == ExecuteType.THREAD_DELETE and exec2.type == ExecuteType.BLOCK:
            return Executor(
                type=ExecuteType.THREAD_DELETE_BLOCK,
                plugin=exec1.plugin,
                sender=exec1.sender,
                thread=exec1.thread,
                day=exec2.day,
                note=f"{exec1.note} | {exec2.note}",
                db_log=exec1.db_log or exec2.db_log,
                std_log=exec1.std_log or exec2.std_log,
            )

        elif exec1.type == ExecuteType.BLOCK and exec2.type == ExecuteType.BLOCK:
            if exec1.day >= exec2.day:
                return exec1
            else:
                return exec2

        elif exec1.type == ExecuteType.COMMENT_DELETE_BLOCK and exec2.type == ExecuteType.COMMENT_DELETE_BLOCK:
            return exec1

        elif exec1.type == ExecuteType.POST_DELETE_BLOCK and exec2.type == ExecuteType.POST_DELETE_BLOCK:
            return exec1

        elif exec1.type == ExecuteType.THREAD_DELETE_BLOCK and exec2.type == ExecuteType.THREAD_DELETE_BLOCK:
            return exec1

    def set_base_info(self, plugin: str = None, sender: str = None):
        self.plugin = plugin
        self.sender = sender

    async def _thread_delete(self, client: Client, user: UserInfo):
        await client.del_thread(self.thread.fid, self.thread.tid)
        await self.log(
            user,
            f"{self.thread.fname}:{self.thread.tid}:{self.thread.user.show_name}",
            f"{self.note} | {cut_string(self.thread.text, 50, '...')}"
        )

    async def _block(self, client: Client, user: UserInfo):
        obj_user = await client.get_user_info(self.user)

        await client.block(self.fname_or_fid, obj_user.portrait, day=self.day, reason=self.note)

        if isinstance(self.fname_or_fid, int):
            fname = await client.get_fname(self.fname_or_fid)
        else:
            fname = self.fname_or_fid

        await self.log(user, f"{fname}:{obj_user.show_name}", self.note)

    async def _post_delete(self, client: Client, user: UserInfo):
        await client.del_post(self.post.fid, self.post.tid, self.post.pid)
        await self.log(
            user,
            f"{self.post.fname}:{self.post.pid}:{self.post.user.show_name}",
            f"{self.note} | {cut_string(self.post.text, 50, '...')}"
        )

    async def _comment_delete(self, client: Client, user: UserInfo):
        await client.del_post(self.comment.fid, self.comment.tid, self.comment.pid)
        await self.log(
            user,
            f"{self.comment.fname}:{self.comment.pid}:{self.comment.user.show_name}",
            f"{self.note} | {cut_string(self.comment.text, 50, '...')}"
        )

    async def _recover_post(self, client: Client, user: UserInfo):
        if isinstance(self.fname_or_fid, int):
            fname = await client.get_fname(self.fname_or_fid)
        else:
            fname = self.fname_or_fid
        await self.log(
            user,
            f"{fname}:{self.context_id}",
            self.note
        )


def empty(db_log=False, std_log=False):
    """
    返回空操作
    Returns:
        Executor
    """
    return Executor(
        ExecuteType.EMPTY,
        db_log=db_log,
        std_log=std_log,
    )


def hide(thread: UnionTbThread,
         note: str = None):
    """
    返回屏蔽主题贴的操作
    Args:
        thread: 待处理主题贴
        note: 调用该方法的方法的名称

    Returns:
        Executor
    """
    return Executor(
        ExecuteType.THREAD_HIDE,
        thread=thread,
        note=note,
    )


def delete(obj: Union[UnionTbThread, UnionTbPost, Tb_Comment],
           day: int = None,
           note: str = None):
    """
    返回删除主题贴的操作
    Args:
        obj: 待处理的主题贴/楼/楼中楼
        day: 对发送者的封禁持续时间（单位：天）-1是永封
        note:

    Returns:
        Executor
    """
    if isinstance(obj, UnionTbThread):
        option = ExecuteType.THREAD_DELETE
        _type = "thread"
    elif isinstance(obj, UnionTbPost):
        option = ExecuteType.POST_DELETE
        _type = "post"
    elif isinstance(obj, Tb_Comment):
        option = ExecuteType.COMMENT_DELETE
        _type = "comment"
    else:
        raise TypeError("不支持的操作类型")

    if day is not None and day != 0:
        match option:
            case ExecuteType.THREAD_DELETE:
                option = ExecuteType.THREAD_DELETE_BLOCK
            case ExecuteType.POST_DELETE:
                option = ExecuteType.POST_DELETE_BLOCK
            case ExecuteType.COMMENT_DELETE:
                option = ExecuteType.COMMENT_DELETE_BLOCK

    if day is None:
        _day = None
    elif day <= -1:
        _day = -1
    elif 1 <= day < 3:
        _day = 1
    elif 3 <= day < 5:
        _day = 3
    elif 5 <= day < 90:
        _day = 10
    else:
        _day = 90

    data = {
        "type": option,
        _type: obj,
        "day": _day,
        "note": note,
    }

    return Executor(**data)


def block(fname_or_id: str | int,
          user: str | int,
          day: int = 1,
          note: str = None):
    """
    返回封禁操作
    Args:
        fname_or_id:
        user:
        day: 封禁时间（单位：天）
        note:

    Returns:
        Executor
    """
    if day <= -1:
        _day = -1
    elif 1 <= day < 3:
        _day = 1
    elif 3 <= day < 5:
        _day = 3
    elif 5 <= day < 90:
        _day = 10
    else:
        _day = 90
    return Executor(
        ExecuteType.BLOCK,
        user=user,
        fname_or_fid=fname_or_id,
        day=day,
        note=note,
    )


def black(fname_or_id: str,
          user: str,
          note: str = None):
    """
    返回加入黑名单操作
    Args:
        fname_or_id:
        user:
        note:

    Returns:
        Executor
    """
    return Executor(
        ExecuteType.BLACK,
        user=user,
        fname_or_fid=fname_or_id,
        note=note,
    )


def set_permission(fname: str,
                   user: str,
                   permission: Permission,
                   note: str):
    return Executor(
        ExecuteType.PERMISSION_EDIT,
        user=user,
        fname_or_fid=fname,
        permission=permission,
        note=note,
    )
