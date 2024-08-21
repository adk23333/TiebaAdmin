from aiotieba import Client
from aiotieba.typing import Thread, Post, Comment
from enum import Enum
from functools import wraps
from typing import Union, Callable, Coroutine, Dict, Any, Literal, List

from core.enum import Permission
from core.models import ForumUserPermission
from . import execute
from .execute import empty, delete, block
from .models import Keyword

CheckFunc = Callable[[Union[Thread, Post, Comment], Client], Coroutine[Any, Any, execute.Executor]]
Check = Dict[Literal['function', 'kwargs'], Union[CheckFunc, Dict]]
CheckMap = Dict[Literal['post', 'comment', 'thread'], List[Check]]


class Level(Enum):
    """
    方便划分等级的魔法数字枚举

    Attributes:
        ALL: {1-18}
        LOW : {1-3}
        MIDDLE : {4-9}
        HIGH : {10-18}
        LOW1 : {1-6}
        MIDDLE2 : {7-12}
        HIGH2 : {13-18}
    """
    ALL = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}
    LOW = {1, 2, 3}
    MIDDLE = {4, 5, 6, 7, 8, 9}
    HIGH = {10, 11, 12, 13, 14, 15, 16, 17, 18}
    LOW1 = {1, 2, 3, 4, 5, 6}
    MIDDLE2 = {7, 8, 9, 10, 11, 12}
    HIGH2 = {13, 14, 15, 16, 17, 18}

    def __add__(self, other):
        """
        使这个类支持使用+符号合并
        """
        return self.value.add(other)


OFFICES_ID = {167570067: "贴吧吧主小管家", }


def ignore_office():
    def wrapper(func: CheckFunc):
        @wraps(func)
        async def decorator(t: Union[Thread, Post, Comment], c):
            if t.user.user_id in OFFICES_ID:
                return empty()
            return await func(t, c)

        return decorator

    return wrapper


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


manager = CheckerManager()


@manager.route(['thread', 'post', 'comment'])
@ignore_office()
async def check_keyword(t: Union[Thread, Post, Comment], client: Client):
    if t.user.level in Level.LOW.value:
        keywords = await Keyword.all()
        for kw in keywords:
            if t.text.find(kw.keyword) != -1:
                return delete(client, t, func_name="check_keyword")
    return empty()


@manager.route(['thread', 'post', 'comment'])
async def check_black(t: Union[Thread, Post, Comment], client: Client):
    user = await ForumUserPermission.filter(user_id=t.user.user_id, permission=Permission.Black.value).get_or_none()
    if user:
        return block(client, t, 10, func_name="check_black")
    return empty()


def _level_wall(level: int, thread: Thread, client: Client):
    if thread.user.level == level:
        return delete(client, thread, func_name="level_wall")
    return empty()


@manager.thread()
@ignore_office()
async def level_wall_1(thread: Thread, client: Client):
    return _level_wall(1, thread, client)


@manager.thread()
@ignore_office()
async def level_wall_3(thread: Thread, client: Client):
    return _level_wall(3, thread, client)
