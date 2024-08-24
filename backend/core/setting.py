import abc
import os.path
import tomllib
from typing import Any, Dict, List, Union

import tomli_w
from sanic.log import logger


class ABCItem(abc.ABC):
    _value: Any = None
    _required = False
    _description: str = None
    _editable = True

    def set(self, _v: Any):
        if self._editable:
            self._value = _v
            return True
        else:
            return False

    def set_value(self, _v: Any):
        self._value = _v
        return self

    def required(self):
        self._required = True
        return self

    def description(self, desc: str):
        self._description = desc
        return self

    def non_editable(self):
        self._editable = False
        return self

    @property
    def json(self):
        return self._value

    def __repr__(self):
        return repr(self._value)

    @property
    def value(self):
        return self._value


class BaseItem(ABCItem):
    _default: Any = None

    @abc.abstractmethod
    def default(self, _value: Any):
        logger.error("Not Implemented")


class ContainItem(ABCItem):

    def __len__(self):
        return len(self._value)


Object_T = Dict[str, ABCItem]


class ObjectItem(ContainItem):
    _value: Object_T
    _default: Object_T

    def __init__(self, _value: Object_T):
        self._default = _value
        self.set_value(self._default)

    def __getitem__(self, item):
        if isinstance(self._value[item], ObjectItem) or isinstance(self._value[item], ListItem):
            return self._value[item]
        else:
            return self._value[item].value

    def __setitem__(self, key, value):
        self._value[key].set(value)

    def items(self):
        return self._value.items()

    @property
    def json(self):
        return {k: v.json for k, v in self.items()}


Dict_T = Dict[str, Any]


class DictItem(ContainItem):
    _value: List[Dict_T] = []
    _table_title: List[str] = None

    def __init__(self, table_title: List[str]):
        if len(table_title) == 0:
            raise TypeError
        self._table_title = table_title

    def __getitem__(self, item: int):
        return self._value[item]

    def __setitem__(self, key: int, value: Dict_T):
        self._check_keys(value)
        self._value[key] = value

    def default(self, _value: List[Dict_T]):
        self._value = _value
        return self

    def append(self, value: Dict_T):
        self._check_keys(value)
        self._value.append(value)

    def pop(self, index: int):
        self._value.pop(index)

    def remove(self, value: Any):
        self._value.remove(value)

    def _check_keys(self, value: Dict[str, Any]):
        if set(self._table_title) != set(value.keys()):
            raise TypeError("输入的字典需要有配置里定义的键")


class ListItem(ContainItem):
    _value: List[Union[int, bool, str]] = []

    def __getitem__(self, item: int):
        return self._value[item]

    def __setitem__(self, key: int, value: Union[int, bool, str]):
        self._value[key] = value

    def default(self, _value: List[Union[int, bool, str]]):
        self._value = _value
        return self

    def append(self, value: Union[int, bool, str]):
        self._value.append(value)

    def pop(self, index: int):
        self._value.pop(index)

    def remove(self, value: Union[int, bool, str]):
        self._value.remove(value)


class StringItem(BaseItem):
    _secret: bool = False
    _link: bool = False
    _textarea: bool = False

    def default(self, _value: str):
        self._default = _value
        self._value = self._default
        return self

    def secret(self):
        self._secret = True
        return self

    def link(self):
        self._link = True
        return self

    def textarea(self):
        self._textarea = True
        return self


class IntItem(BaseItem):
    _min: int = None
    _max: int = None
    _step: int = None

    def default(self, _value: int):
        self._default = _value
        self._value = self._default
        return self

    def min(self, _v):
        self._min = _v
        return self

    def max(self, _v):
        self._max = _v
        return self

    def step(self, _v):
        self._step = _v
        return self


class BoolItem(BaseItem):
    _value: bool = None
    _default: bool = None

    def default(self, _value: bool):
        self._default = _value
        self._value = self._default
        return self


class ConfigManager(ObjectItem):
    def __init__(self, path: str, _value: dict[str, ABCItem]):
        super().__init__(_value)
        self.path = path

    @classmethod
    def object(cls, _value: dict[str, ABCItem]):
        return ObjectItem(_value)

    @classmethod
    def dict(cls, table_title: list[str]):
        return DictItem(table_title)

    @classmethod
    def list(cls):
        return ListItem()

    @classmethod
    def string(cls):
        return StringItem()

    @classmethod
    def int(cls):
        return IntItem()

    @classmethod
    def bool(cls):
        return BoolItem()

    def dumps(self):
        return tomli_w.dumps(self.json)

    def dump(self):
        if self.value is not None:
            with open(self.path, "wb") as fp:
                tomli_w.dump(self.json, fp)

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "rb") as fp:
                data = tomllib.load(fp)
            self._to_config(self, data)
            return True
        else:
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dump()
        if exc_tb is not None:
            raise exc_val

    @staticmethod
    def _to_config(obj: "ObjectItem", data: Dict[str, Any]):
        for k, v in obj.items():
            if isinstance(v, ObjectItem):
                ConfigManager._to_config(v, data[k])
            else:
                obj._value[k].set_value(data[k])
        return obj


server_config = ConfigManager("./config.toml", {
    "cache_path": ConfigManager.string().default("./.cache").description("缓存文件目录"),
    "cache_file": ConfigManager.string().default("db.sqlite").description("缓存文件名"),
    "first_start": ConfigManager.bool().default(True).description("第一次启动").non_editable(),
    "version": ConfigManager.string().default("2.0.0").description("版本号"),
    "server": ConfigManager.object({
        "host": ConfigManager.string().default("0.0.0.0").description("监听地址"),
        "port": ConfigManager.int().default(3100).description("监听端口"),
        "workers": ConfigManager.int().default(1).description("工作进程数"),
        "web": ConfigManager.bool().default(True).description("是否启动网页"),
        "secret": ConfigManager.string().default("This is a big secret!!!").description("加密密钥"),
        "db_url": ConfigManager.string().default("sqlite://./.cache/db.sqlite").description("数据库地址"),
        "dev": ConfigManager.bool().default(False).description("开发模式"), }
    ).description("服务器启动项"),
    "extend": ConfigManager.object({
        "review": ConfigManager.object({
            "dev": ConfigManager.bool().default(False).description("只审查不执行操作"),
            "forums": ConfigManager.dict(["forum", "user_id"]),
            "functions": ConfigManager.dict(["forum", "function"]),
            "keywords": ConfigManager.list(),
        }),
    }),
}).description("服务器配置文件")
