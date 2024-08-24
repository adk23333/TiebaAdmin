import os
from unittest import IsolatedAsyncioTestCase

from tortoise import Tortoise, connections

from core.models import ForumPermission
from extend.review.reviewer import Reviewer


class TestReview(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://./.cache/db2.sqlite",
                            modules={'models': ['core.models', 'extend.review.models']})
        await Tortoise.generate_schemas()
        self.review = Reviewer()

    async def test_review(self):
        fp = await ForumPermission.get(user_id=os.environ["TEST_USER_ID"], forum=os.environ["TEST_FORUM_NAME"])
        self.review.forums = [fp, ]
        await self.review.start()

    async def asyncTearDown(self):
        await connections.close_all()
