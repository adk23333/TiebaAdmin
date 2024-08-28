import aiotieba
from sanic.logging.loggers import logger

from core.models import ForumPermission, User
from core.types import TBApp


async def init_tieba_clients(app: TBApp):
    fps = await ForumPermission.filter(is_executor=True).all()
    users = [i.user_id for i in fps]
    users = set(users)
    users = [await User.get(user_id=user) for user in users]
    for user in users:
        async with aiotieba.Client(user.BDUSS, user.STOKEN) as client:
            if getattr(app.ctx, "tb_client", None) is None:
                app.ctx.tb_client = {}
            app.ctx.tb_client[user.user_id] = client
            logger.debug(f"active {user.username} client.")
