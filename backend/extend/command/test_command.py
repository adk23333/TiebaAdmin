import os
import unittest

from aiotieba import Client
from tortoise import Tortoise, connections

from core.models import User
from .handle import CommandHandle


class TestCommand(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://./.cache/db2.sqlite",
                            modules={'models': ['core.models', 'extend.review.models']})
        await Tortoise.generate_schemas()
        self.command = CommandHandle()

    async def test_command(self):
        user = await User.get(user_id=os.environ["TEST_USER_ID"])
        self.command.db_listener = user
        self.command.forums = os.environ["TEST_FORUMS"].split(",")
        async with Client(user.BDUSS, user.STOKEN) as client:
            await self.command._start(client)

    async def asyncTearDown(self):
        await connections.close_all()
