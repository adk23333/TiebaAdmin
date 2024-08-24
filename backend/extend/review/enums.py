from enum import Enum


class Level(Enum):
    """
    方便划分等级的魔法数字枚举

    Attributes:
        ALL: {1-18}
        LOW : {1-3}
        MIDDLE : {4-9}
        HIGH : {10-18}
        LOW1 : {1-6}
        MIDDLE2 : {7-12}
        HIGH2 : {13-18}
    """
    ALL = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}
    LOW = {1, 2, 3}
    MIDDLE = {4, 5, 6, 7, 8, 9}
    HIGH = {10, 11, 12, 13, 14, 15, 16, 17, 18}
    LOW1 = {1, 2, 3, 4, 5, 6}
    MIDDLE2 = {7, 8, 9, 10, 11, 12}
    HIGH2 = {13, 14, 15, 16, 17, 18}

    def __add__(self, other):
        """
        使这个类支持使用+符号合并
        """
        return self.value.add(other)
