from enum import unique, Enum, IntEnum


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
