from enum import unique, IntFlag, auto


class Permission(IntFlag):
    """
    权限枚举

    Attributes:
        MASTER: 管理员，大吧主
        SUPER_ADMIN: 大吧主权限
        HIGH_ADMIN: 高权限吧务权限
        MIN_ADMIN: 小吧主权限
        CREATOR: 优秀创作者权限
        ORDINARY: 普通成员权限
        BLACK: 黑名单权限
    """
    MASTER = auto()
    SUPER_ADMIN = auto()
    HIGH_ADMIN = auto()
    MIN_ADMIN = auto()
    CREATOR = auto()
    ORDINARY = auto()
    BLACK = auto()

    ALL = BLACK | ORDINARY | CREATOR | MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_ORDINARY = ORDINARY | CREATOR | MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_CREATOR = CREATOR | MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_MIN_ADMIN = MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_HIGH_ADMIN = HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_SUPER_ADMIN = SUPER_ADMIN | MASTER

    @property
    def scopes(self):
        return [i.name for i in self]


@unique
class ExecuteType(IntFlag):
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
    Empty = auto()
    PermissionEdit = auto()

    TiebaPermissionEdit = auto()

    ThreadHide = auto()
    ThreadDelete = auto()

    PostDelete = auto()

    CommentDelete = auto()

    Block = auto()
    Black = auto()

    Good = auto()
