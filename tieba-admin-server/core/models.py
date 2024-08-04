import json
from datetime import datetime
from enum import IntEnum, unique, Enum
from typing import Any, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sanic_jwt.exceptions import AuthenticationFailed
from tortoise import Model, fields
from tortoise.exceptions import DoesNotExist


@unique
class Permission(Enum):
    """
    权限枚举
    
    Attributes:
        Master : 管理员，大吧主
        SuperAdmin : 大吧主权限
        HighAdmin : 高权限吧务权限
        MinAdmin : 小吧主权限
        Creator : 优秀创作者权限
        Ordinary : 普通成员权限
        Black : 黑名单权限
    """
    Master = "master"
    SuperAdmin = "super"
    HighAdmin = "high"
    MinAdmin = "min"
    Creator = "creator"
    Ordinary = "ordinary"
    Black = "black"

    @classmethod
    def all(cls):
        return [cls.Black.value, cls.Ordinary.value, cls.Creator.value, cls.MinAdmin.value,
                cls.HighAdmin.value, cls.SuperAdmin.value, cls.Master.value]

    @classmethod
    def ordinary(cls):
        return [cls.Ordinary.value, cls.Creator.value, cls.MinAdmin.value,
                cls.HighAdmin.value, cls.SuperAdmin.value, cls.Master.value]

    @classmethod
    def creator(cls):
        return [cls.Creator.value, cls.MinAdmin.value, cls.HighAdmin.value,
                cls.SuperAdmin.value, cls.Master.value]

    @classmethod
    def min(cls):
        return [cls.MinAdmin.value, cls.HighAdmin.value, cls.SuperAdmin.value,
                cls.Master.value]

    @classmethod
    def high(cls):
        return [cls.HighAdmin.value, cls.SuperAdmin.value, cls.Master.value]

    @classmethod
    def super(cls):
        return [cls.SuperAdmin.value, cls.Master.value]

    @classmethod
    def master(cls):
        return [cls.Master.value, ]


class Config(Model):
    """
    存储简单的配置的表
    """
    key = fields.CharField(max_length=32)
    v1 = fields.CharField(max_length=256)

    class Meta:
        table = "configs"

    @staticmethod
    async def get_bool(key: str) -> Optional[bool]:
        rst = await Config.filter(key=key).get_or_none()
        if rst:
            return rst.v1 == str(True)
        else:
            return None

    @staticmethod
    async def get_list(key: str) -> Optional[bool]:
        rst = await Config.filter(key=key).get_or_none()
        if rst:
            return json.loads(rst.v1)

    @staticmethod
    async def set_config(key: str, v1: Any):
        rst = await Config.filter(key=key).get_or_none()
        if not rst:
            rst = Config(key=key, v1=str(v1))
        rst.v1 = str(v1)
        await rst.save()


class User(Model):
    """
    存储账号信息
    Attributes:
        uid : 贴吧用户id
        tuid : 贴吧用户的uid
        username : 贴吧用户username
        password : 登录本站的密码
        BDUSS :
        STOKEN : 
        master : 归属该账户管辖
    """
    uid = fields.BigIntField(pk=True)
    tuid = fields.BigIntField(null=True, default=None)
    username = fields.CharField(max_length=64)
    password = fields.CharField(max_length=128, null=True, default=None)
    BDUSS = fields.CharField(max_length=200, null=True, default='')
    STOKEN = fields.CharField(max_length=80, null=True, default='')
    master = fields.BigIntField(null=True, default=None)
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

    @staticmethod
    async def get_via_uid(tuid: int):
        try:
            user = await User.filter(tuid=tuid).get()
            return user
        except DoesNotExist:
            raise AuthenticationFailed("用户名或密码不正确")

    async def verify_password(self, password_hasher: PasswordHasher, password: str):
        try:
            password_hasher.verify(self.password, password)
            if password_hasher.check_needs_rehash(self.password):
                self.password = password_hasher.hash(password)
                await self.save(update_fields=["password"])
        except VerifyMismatchError:
            raise AuthenticationFailed("用户名或密码不正确")

    def to_dict(self):
        return {
            "uid": self.uid,
            "tuid": self.tuid,
            "username": self.username,
        }


class ForumUserPermission(Model):
    """
    记录需要管理的贴吧以及其对应管理账户及权限的表

    Attributes:
        fid: 贴吧id
        fname: 贴吧名字
        user: 管理该吧的账号
        permission: 权限
    """
    fid = fields.IntField()
    fname = fields.CharField(max_length=128)
    user = fields.ForeignKeyField("models.User")
    permission = fields.CharField(max_length=128, default=Permission.Ordinary.value)
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "forum_user_permission"

    async def to_dict(self):
        t = {
            "fid": self.fid,
            "fname": self.fname,
            "permission": self.permission,
        }
        t.update((await self.user.get()).to_dict())
        return t


class ExecuteLog(Model):
    """
    记录所有有必要公开的操作记录

    Attributes:
        user : 执行操作的主体
        type : 操作类型
        note : 备注
        date_created: 执行时间
        date_updated: 最后修改时间
    """
    id = fields.BigIntField(pk=True)
    user = fields.CharField(64)
    type = fields.IntField()
    obj = fields.CharField(64)
    note = fields.TextField(default="")
    date_created: datetime = fields.DatetimeField(auto_now_add=True)
    date_updated: datetime = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "execute_log"

    async def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "type": ExecuteType(self.type).name,
            "obj": self.obj,
            "note": self.note,
            "date_created": str(self.date_created.strftime("%Y-%m-%d %H:%M:%S")),
            "date_updated": str(self.date_updated.strftime("%Y-%m-%d %H:%M:%S")),
        }


@unique
class ExecuteType(IntEnum):
    """
    操作类型
    
    Attributes:
        Empty: 无操作
        PermissionEdit: 修改本站用户权限
    
        TiebaPermissionEdit: 修改贴吧用户权限

        ThreadDelete: 删除主题贴
        ThreadHide: 屏蔽主题贴
        
        PostDelete: 删除楼层

        CommentDelete: 删除楼中楼
        
        Block: 封禁用户
        Black: 将用户加入黑名单

        Good: 加精
        
    """
    Empty = 0
    PermissionEdit = 1

    TiebaPermissionEdit = 100

    ThreadHide = 110
    ThreadDelete = 111

    PostDelete = 120

    CommentDelete = 130

    Block = 140
    Black = 141

    Good = 150
