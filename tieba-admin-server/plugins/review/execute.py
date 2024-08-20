from dataclasses import dataclass
from typing import Union, Literal

from aiotieba import Client
from aiotieba.typing import Comment as Tb_Comment
from aiotieba.typing import Post as Tb_Post
from aiotieba.typing import Thread as Tb_Thread
from aiotieba.typing import UserInfo
from sanic.log import logger

from core.enum import ExecuteType
from core.models import ExecuteLog

BOT_PRE = "ReviewBot"


@dataclass
class Executor(object):
    """操作容器类

    所有操作都应该使用此类包装后统一处理.

    Attributes:
        client: 传入了执行账号的贴吧客户端.
        obj: 待处理的贴子.
        user_opt: 对待处理贴子的发送者的处理.
        option: 对贴子的处理.
        user_day: 对发送者的操作持续时间.
        opt_day: 对贴子的操作持续时间.
    """
    client: Client = None
    obj: Union[Tb_Thread, Tb_Post, Tb_Comment, None] = None
    user_opt: ExecuteType = ExecuteType.Empty
    option: ExecuteType = ExecuteType.Empty
    user_day: int = 0
    opt_day: int = 0
    note: set[str] = ()

    async def run(self):
        """
        执行操作
        Returns:
            None

        """

        note = ""
        for i in self.note:
            note += f",{i}"
        note = note[1:]

        user: UserInfo = await self.client.get_self_info()
        rst = True
        match self.user_opt:
            case ExecuteType.Empty:
                pass
            case ExecuteType.Block:
                rst = await self.client.block(self.obj.fid, self.obj.user.portrait, day=self.user_day)
                await ExecuteLog.create(user=f"[{BOT_PRE}] {user.user_name}",
                                        type=ExecuteType.Block,
                                        obj=self.obj.user.user_name,
                                        note=f"[{note}] {self.user_day}")
            case ExecuteType.Black:
                rst = await self.client.add_bawu_blacklist(self.obj.fname, self.obj.user.portrait)
                await ExecuteLog.create(user=f"[{BOT_PRE}] {user.user_name}",
                                        type=ExecuteType.Black,
                                        obj=self.obj.user.user_name,
                                        note=f"[{note}]")
        if not rst:
            logger.warning(rst.err)
        rst = True
        match self.option:
            case ExecuteType.Empty:
                pass
            case ExecuteType.ThreadHide:
                rst = await self.client.hide_thread(self.obj.fid, self.obj.tid)
                await ExecuteLog.create(user=f"[{BOT_PRE}] {user.user_name}",
                                        type=ExecuteType.Hide,
                                        obj=str(self.obj.tid),
                                        note=f"[{note}] {self.obj.text}")

            case ExecuteType.ThreadDelete:
                rst = await self.client.del_thread(self.obj.fid, self.obj.tid)
                await ExecuteLog.create(user=f"[{BOT_PRE}]{user.user_name}",
                                        type=ExecuteType.ThreadDelete,
                                        obj=str(self.obj.tid),
                                        note=f"[{note}] {self.obj.text}")

            case ExecuteType.PostDelete:
                rst = await self.client.del_post(self.obj.fid, self.obj.tid, self.obj.pid)
                await ExecuteLog.create(user=f"[{BOT_PRE}]{user.user_name}",
                                        type=ExecuteType.PostDelete,
                                        obj=str(self.obj.pid),
                                        note=f"[{note}] {self.obj.text}")

            case ExecuteType.CommentDelete:
                rst = await self.client.del_post(self.obj.fid, self.obj.tid, self.obj.pid)
                await ExecuteLog.create(user=f"[{BOT_PRE}]{user.user_name}",
                                        type=ExecuteType.CommentDelete,
                                        obj=str(self.obj.pid),
                                        note=f"[{note}] {self.obj.text}")
        if not rst:
            logger.warning(rst.err)

    def exec_compare(self, exec2):
        """
        与exec2比较处罚严重程度，返回包含更严重操作的新操作类
        Args:
            exec2 (Executor): 待比较操作类

        Returns:
            Executor

        """
        self.note = set(self.note)

        if exec2.user_opt > self.user_opt:
            self.user_opt = exec2.user_opt
            self.user_day = exec2.user_day
            self.note.update(exec2.note)

        elif exec2.user_opt == self.user_opt and exec2.user_day > self.user_day:
            self.user_day = exec2.user_day
            self.note.update(exec2.note)

        if exec2.option > self.option:
            self.option = exec2.option
            self.note.update(exec2.note)

        elif exec2.option == self.option and exec2.opt_day > self.opt_day:
            self.opt_day = exec2.opt_day
            self.note.update(exec2.note)

    def __str__(self):
        return str(self.__dict__)

    @property
    def __dict__(self):
        return {
            "obj": self.obj.__dict__,
            "user_opt": self.user_opt.name,
            "option": self.option.name,
            "user_day": self.user_day,
            "opt_day": self.opt_day
        }


def empty():
    """
    返回空操作
    Returns:
        Executor
    """
    return Executor()


def hide(client: Client, thread: Tb_Thread, day: int = 1, func_name: str = ""):
    """
    返回屏蔽主题贴的操作
    Args:
        client: 传入了执行账号的贴吧客户端
        thread: 待处理主题贴
        day: 屏蔽持续时间（单位：天）
        func_name: 调用该方法的方法的名称

    Returns:
        Executor
    """
    return Executor(
        client,
        thread,
        option=ExecuteType.ThreadHide,
        opt_day=day,
        note={func_name},
    )


def delete(client: Client,
           obj: Union[Tb_Thread, Tb_Post, Tb_Comment],
           day: Literal[-1, 0, 1, 3, 10] = 0,
           func_name: str = ""):
    """
    返回删除主题贴的操作
    Args:
        client: 传入了执行账号的贴吧客户端
        obj: 待处理的主题贴/楼/楼中楼
        day: 对发送者的封禁持续时间（单位：天）-1是永封
        func_name: 调用该方法的方法的名称

    Returns:
        Executor
    """
    if isinstance(obj, Tb_Thread):
        option = ExecuteType.ThreadDelete
    elif isinstance(obj, Tb_Post):
        option = ExecuteType.PostDelete
    elif isinstance(obj, Tb_Comment):
        option = ExecuteType.CommentDelete
    else:
        option = ExecuteType.Empty

    if day:
        if day == -1:
            user_opt = ExecuteType.Black
        else:
            user_opt = ExecuteType.Block
        return Executor(
            client,
            obj,
            option=option,
            user_opt=user_opt,
            user_day=day,
            note={func_name},
        )
    else:
        return Executor(
            client,
            obj,
            option=option,
            note={func_name},
        )


def block(client: Client,
          obj: Union[Tb_Thread, Tb_Post, Tb_Comment],
          day: Literal[1, 3, 10] = 1,
          func_name: str = ""):
    """
    返回封禁操作
    Args:
        client: 传入了执行账号的贴吧客户端
        obj: 待处理的主题贴/楼/楼中楼
        day: 封禁时间（单位：天）
        func_name: 调用该方法的方法的名称

    Returns:
        Executor
    """
    return Executor(
        client,
        obj,
        user_opt=ExecuteType.Block,
        user_day=day,
        note={func_name},
    )


def black(client: Client, obj: Union[Tb_Thread, Tb_Post, Tb_Comment], func_name: str = ""):
    """
    返回加入黑名单操作
    Args:
        client: 传入了执行账号的贴吧客户端
        obj: 待处理的主题贴/楼/楼中楼
        func_name: 调用该方法的方法的名称

    Returns:
        Executor
    """
    return Executor(
        client,
        obj,
        user_opt=ExecuteType.Black,
        note={func_name},
    )
