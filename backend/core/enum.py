from enum import IntFlag, auto, StrEnum


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
    MASTER = 0
    SUPER_ADMIN = 1
    HIGH_ADMIN = 2
    MIN_ADMIN = 4
    CREATOR = 8
    ORDINARY = 16
    BLACK = 32

    ALL = BLACK | ORDINARY | CREATOR | MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_ORDINARY = ORDINARY | CREATOR | MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_CREATOR = CREATOR | MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_MIN_ADMIN = MIN_ADMIN | HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_HIGH_ADMIN = HIGH_ADMIN | SUPER_ADMIN | MASTER
    GE_SUPER_ADMIN = SUPER_ADMIN | MASTER

    @property
    def scopes(self):
        return [i.name for i in self]

    @classmethod
    def convert_zh(cls, value: str):
        p_map = {'超级管理员': cls.MASTER, '大吧主': cls.SUPER_ADMIN, '高权限小吧主': cls.HIGH_ADMIN,
                 '小吧主': cls.MIN_ADMIN, '创作者': cls.CREATOR, '黑名单': cls.BLACK}
        return p_map.get(value, None)


class ExecuteType(StrEnum):
    """
    操作类型

    Attributes:
        EMPTY: 无操作
        PERMISSION_EDIT: 修改本站用户权限

        TIEBA_PERMISSION_EDIT: 修改贴吧用户权限

        COMMENT_DELETE: 删除楼中楼

        POST_DELETE: 删除楼层

        THREAD_DELETE: 删除主题贴
        THREAD_HIDE: 屏蔽主题贴
        THREAD_GOOD: 加精

        BLOCK: 封禁用户
        BLACK: 将用户加入黑名单


    """
    EMPTY = auto()
    PERMISSION_EDIT = auto()

    TIEBA_PERMISSION_EDIT = auto()
    TIEBA_GET_INFO = auto()

    COMMENT_DELETE = auto()
    COMMENT_DELETE_BLOCK = auto()
    COMMENT_RECOVER = auto()

    POST_DELETE = auto()
    POST_DELETE_BLOCK = auto()
    POST_RECOVER = auto()

    THREAD_HIDE = auto()
    THREAD_UN_HIDE = auto()
    THREAD_DELETE = auto()
    THREAD_DELETE_BLOCK = auto()
    THREAD_RECOVER = auto()

    THREAD_GOOD = auto()
    THREAD_UN_GOOD = auto()
    THREAD_RECOMMEND = auto()
    THREAD_MOVE = auto()
    THREAD_TOP = auto()
    THREAD_UN_TOP = auto()

    BLOCK = auto()
    UN_BLOCK = auto()
    BLACK = auto()
    UN_BLACK = auto()

    @classmethod
    def delete(cls):
        return (
            cls.THREAD_DELETE,
            cls.THREAD_DELETE_BLOCK,
            cls.POST_DELETE,
            cls.POST_DELETE_BLOCK,
            cls.COMMENT_DELETE,
            cls.COMMENT_DELETE_BLOCK
        )
