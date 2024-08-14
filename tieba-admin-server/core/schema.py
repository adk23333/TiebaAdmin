import abc
import os.path
import tomllib
from typing import Any, Dict, List, TypeVar, Generic

import tomli_w
from sanic.log import logger

ListItemType = TypeVar("ListItemType")


class BaseItem(abc.ABC):
    _value: Any = None
    _required = False
    _default: Any = None
    _description: str = None
    _editable = True

    def required(self):
        self._required = True
        return self

    def non_editable(self):
        self._editable = False
        return self

    @abc.abstractmethod
    def default(self, _value: Any):
        logger.error("Not Implemented")

    def description(self, desc: str):
        self._description = desc
        return self

    def set(self, _v: Any):
        if self._editable:
            self._value = _v
            return True
        else:
            return False

    def set_value(self, _v: Any):
        self._value = _v
        return self

    @property
    def json(self):
        return self._value

    def __repr__(self):
        return repr(self._value)

    @property
    def value(self):
        return self._value


class DictItem(BaseItem):
    _value: Dict[str, BaseItem]
    _default: Dict[str, BaseItem]

    def __getitem__(self, item):
        if isinstance(self._value[item], DictItem) or isinstance(self._value[item], ListItem):
            return self._value[item]
        else:
            return self._value[item].value

    def __setitem__(self, key, value):
        self._value[key].set(value)

    def __len__(self):
        return len(self._value)

    def items(self):
        return self._value.items()

    def default(self, _value: Dict[str, BaseItem]):
        self._default = _value
        self.set_value(self._default)
        return self

    @property
    def json(self):
        return {k: v.json for k, v in self.items()}


class ListItem(Generic[ListItemType], BaseItem):
    _value: List[ListItemType]
    _default: List[ListItemType]

    def __getitem__(self, item: int):
        return self._value[item]

    def __setitem__(self, key: int, value):
        self._value[key] = value

    def __len__(self):
        return len(self._value)

    def default(self, _value: List):
        self._default = _value
        self._value = self._default
        return self

    def append(self, value: Any):
        self._value.append(value)

    def pop(self, index: int):
        self._value.pop(index)

    def remove(self, value: Any):
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


class SchemaManager(DictItem):
    def __init__(self, path: str):
        self.path = path

    @classmethod
    def dict(cls, _v: Dict[str, BaseItem]):
        return DictItem().set_value(_v)

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

    @staticmethod
    def _to_config(obj: DictItem, data: Dict[str, Any]):
        for k, v in obj.items():
            if isinstance(v, DictItem):
                SchemaManager._to_config(v, data[k])
            else:
                obj._value[k].set_value(data[k])
        return obj

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "rb") as fp:
                data = tomllib.load(fp)
            SchemaManager._to_config(self, data)
            return True
        else:
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dump()
        if exc_tb is not None:
            raise exc_val


server_config = SchemaManager("./config.toml").default({
    "cache_path": SchemaManager.string().default("./.cache").description("缓存文件目录"),
    "cache_file": SchemaManager.string().default("db.sqlite").description("缓存文件名"),
    "first_start": SchemaManager.bool().default(True).description("第一次启动").non_editable(),
    "version_code": SchemaManager.string().default("2.0.0").description("版本号"),
    "server": SchemaManager.dict({
        "host": SchemaManager.string().default("0.0.0.0").description("监听地址"),
        "port": SchemaManager.int().default(3100).description("监听端口"),
        "workers": SchemaManager.int().default(1).description("工作进程数"),
        "web": SchemaManager.bool().default(True).description("是否启动网页"),
        "secret": SchemaManager.string().default("This is a big secret!!!").description("加密密钥"),
        "db_url": SchemaManager.string().default("sqlite://./.cache/db.sqlite").description("数据库地址"),
        "dev": SchemaManager.bool().default(False).description("开发模式"), }
    ).description("服务器启动项"), }
).description("服务器配置文件")
