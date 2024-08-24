from dataclasses import dataclass
from functools import wraps
from typing import Callable, Union, Coroutine, Any, Dict, Literal, List

from aiotieba import Client
from aiotieba.api.get_comments import Comment, Comment as Tb_Comment
from aiotieba.api.get_posts import Post, Post as Tb_Post
from aiotieba.api.get_threads import Thread, Thread as Tb_Thread
from aiotieba.typing import UserInfo
from sanic.logging.loggers import logger

from core.enum import ExecuteType
from core.models import ExecuteLog
from core.utils import cut_string

BOT_PREFIX = "Bot"


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

        note = ",".join(self.note)

        user: UserInfo = await self.client.get_self_info()
        rst = True
        match self.user_opt:
            case ExecuteType.Empty:
                pass
            case ExecuteType.Block:
                rst = await self.client.block(self.obj.fid, self.obj.user.portrait, day=self.user_day)
                await ExecuteLog.create(plugin="review",
                                        user=f"[{BOT_PREFIX}] {user.user_name}",
                                        type=ExecuteType.Block,
                                        obj=self.obj.user.user_name,
                                        note=f"[{note}] {self.user_day}")
            case ExecuteType.Black:
                rst = await self.client.add_bawu_blacklist(self.obj.fname, self.obj.user.portrait)
                await ExecuteLog.create(plugin="review",
                                        user=f"[{BOT_PREFIX}] {user.user_name}",
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
                await ExecuteLog.create(plugin="review",
                                        user=f"[{BOT_PREFIX}] {user.user_name}",
                                        type=ExecuteType.Hide,
                                        obj=str(self.obj.tid),
                                        note=f"[{note}] {self.obj.title}")

            case ExecuteType.ThreadDelete:
                rst = await self.client.del_thread(self.obj.fid, self.obj.tid)
                await ExecuteLog.create(plugin="review",
                                        user=f"[{BOT_PREFIX}]{user.user_name}",
                                        type=ExecuteType.ThreadDelete,
                                        obj=str(self.obj.tid),
                                        note=f"[{note}] {self.obj.title}")

            case ExecuteType.PostDelete:
                rst = await self.client.del_post(self.obj.fid, self.obj.tid, self.obj.pid)
                await ExecuteLog.create(plugin="review",
                                        user=f"[{BOT_PREFIX}]{user.user_name}",
                                        type=ExecuteType.PostDelete,
                                        obj=str(self.obj.pid),
                                        note=f"[{note}] {cut_string(self.obj.text, 20, '...')}")

            case ExecuteType.CommentDelete:
                rst = await self.client.del_post(self.obj.fid, self.obj.tid, self.obj.pid)
                await ExecuteLog.create(plugin="review",
                                        user=f"[{BOT_PREFIX}]{user.user_name}",
                                        type=ExecuteType.CommentDelete,
                                        obj=str(self.obj.pid),
                                        note=f"[{note}] {cut_string(self.obj.text, 20, '...')}")
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
        return str(self.json)

    @property
    def json(self):
        return {
            "obj": self.obj.__dict__,
            "user_opt": self.user_opt.name,
            "option": self.option.name,
            "user_day": self.user_day,
            "opt_day": self.opt_day
        }


CheckFunc = Callable[[Union[Thread, Post, Comment], Client], Coroutine[Any, Any, Executor]]
Check = Dict[Literal['function', 'kwargs'], Union[CheckFunc, Dict]]
CheckMap = Dict[Literal['post', 'comment', 'thread'], List[Check]]
OFFICES_ID = {167570067: "贴吧吧主小管家", }


class CheckerManager:
    def __init__(self):
        self.check_map: CheckMap = {'comment': [], 'post': [], 'thread': []}
        self.check_name_map = set()

    def comment(self, description: str = None):
        """
        加载处理楼中楼的checker
        Args:
            description: 已废除的参数
        """

        def wrapper(func: CheckFunc):
            self.check_name_map.add(func.__name__)
            self.check_map['comment'].append({
                'function': func,
                'kwargs': {
                    'description': description,
                },
            })
            return func

        return wrapper

    def post(self, description: str = None):
        """
        加载处理楼层的checker
        Args:
            description: 已废除的参数
        """

        def wrapper(func: CheckFunc):
            self.check_name_map.add(func.__name__)
            self.check_map['post'].append({
                'function': func,
                'kwargs': {
                    'description': description,
                },
            })
            return func

        return wrapper

    def thread(self, description: str = None):
        """
        加载处理主题贴的checker
        Args:
            description: 已废除的参数
        """

        def wrapper(func: CheckFunc):
            self.check_name_map.add(func.__name__)
            self.check_map['thread'].append({
                'function': func,
                'kwargs': {
                    'description': description,
                },
            })
            return func

        return wrapper

    def route(self,
              _type: List[Literal['thread', 'post', 'comment']],
              description: str = None):
        """
        加载处理楼中楼/楼层/主题贴的checker
        Args:
            _type: 处理类型
            description: 已废除的参数
        """

        def wrapper(func: CheckFunc):
            self.check_name_map.add(func.__name__)
            for __type in _type:
                if not (__type == 'thread' or __type == 'post' or __type == 'comment'):
                    raise TypeError
                self.check_map[__type].append({
                    'function': func,
                    'kwargs': {
                        'description': description,
                    },
                })
            return func

        return wrapper


def ignore_office():
    def wrapper(func: CheckFunc):
        @wraps(func)
        async def decorator(t: Union[Thread, Post, Comment], c):
            if t.user.user_id in OFFICES_ID:
                return empty()
            return await func(t, c)

        return decorator

    return wrapper


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
