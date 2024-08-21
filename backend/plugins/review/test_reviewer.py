import unittest
from tortoise import Tortoise

from .reviewer import Reviewer

REVIEW_MODEL = "review.models"
DB_CONFIG = {
    'connections': {
        'default': "sqlite://../../.cache/db.sqlite"
    },
    'apps': {
        'models': {
            "models": ["core.models", REVIEW_MODEL],
            'default_connection': 'default',
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}


class MyTestCase(unittest.IsolatedAsyncioTestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

    async def test_init(self):
        await Tortoise.init(config=DB_CONFIG)
        await Reviewer.init_plugin()

    async def test_run(self):
        reviewer = Reviewer()
        reviewer.PLUGIN_MODEL = REVIEW_MODEL

        await reviewer._start_plugin_with_process(
            db_config=DB_CONFIG,
            log_level="DEBUG",
        )


if __name__ == '__main__':
    unittest.main()
