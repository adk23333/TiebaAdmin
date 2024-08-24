from typing import Union

from aiotieba import Client
from aiotieba.typing import Thread, Post, Comment

from core.enum import Permission
from core.models import ForumPermission
from core.setting import server_config
from .checker_manage import CheckerManager, ignore_office, empty, delete, block
from .enums import Level

manager = CheckerManager()


@manager.route(['thread', 'post', 'comment'])
@ignore_office()
async def check_keyword(t: Union[Thread, Post, Comment], client: Client):
    if t.user.level in Level.LOW.value:
        keywords = server_config["extend"]["review"]["keywords"]
        for kw in keywords:
            if t.text.find(kw) != -1:
                return delete(client, t, func_name="check_keyword")
    return empty()


@manager.route(['thread', 'post', 'comment'])
async def check_black(t: Union[Thread, Post, Comment], client: Client):
    fp = await ForumPermission.get_or_none(user_id=t.user.user_id, forum=t.fname)
    if fp.permission == Permission.BLACK:
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
