from datetime import datetime

from tortoise import Model, fields


class Thread(Model):
    """
    记录已加入检查队列的主题贴

    Notes: 有记录的主题贴不代表已经检查过，当检查过程中终止程序，可能会有主题贴未被检查
    """
    tid = fields.BigIntField(pk=True)
    fid = fields.BigIntField()
    last_time = fields.BigIntField()
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "review_thread"


class Post(Model):
    """
    记录已加入检查队列的楼层及楼中楼

    Notes: 有记录的楼层及楼中楼不代表已经检查过，当检查过程中终止程序，可能会有楼层及楼中楼未被检查
    """
    pid = fields.BigIntField(pk=True)
    tid = fields.BigIntField()
    ppid = fields.BigIntField(null=True, default=None)
    reply_num = fields.IntField(null=True, default=None)
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "review_post"


class Forum(Model):
    """
    记录需要监控的吧
    """
    fname = fields.CharField(max_length=60, pk=True)
    enable = fields.BooleanField(default=False)
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "review_forum"

    def to_json(self):
        return {
            "fname": self.fname,
            "enable": self.enable,
        }


class Function(Model):
    """
    记录需要使用的方法
    """
    function = fields.CharField(max_length=64, pk=True)
    enable = fields.BooleanField(default=False)
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "review_function"

    async def to_json(self):
        return {
            "function": self.function,
            "enable": self.enable,
        }


class Keyword(Model):
    """
    记录关键词检查所使用的关键词
    """
    keyword = fields.CharField(max_length=64, pk=True)

    class Meta:
        table = "review_keyword"
