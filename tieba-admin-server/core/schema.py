import abc
import os.path
from typing import Any, Dict, List, Optional

import yaml
from sanic.log import logger


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

    def _json(self):
        return {
            "required": self._required,
            "default": self._default,
            "description": self._description,
            "editable": self._editable,
        }

    @property
    @abc.abstractmethod
    def json(self):
        value = self._json()
        value["value"] = str(self._value)
        return value

    def __repr__(self):
        return repr(self._value)

    @property
    def value(self):
        return self._value


class DictItem(BaseItem):
    def __getitem__(self, item):
        return self._value[item]

    def __setitem__(self, key, value):
        self._value[key].set(value)

    def __len__(self):
        return len(self._value)

    def items(self):
        return self._value.items()

    def default(self, _value: Dict[str, BaseItem]):
        self._default = _value
        self._value = self._default
        return self

    @property
    def json(self):
        _value = {k: v.json for k, v in self.items()}
        value = self._json()
        value["value"] = _value
        return value


class ListItem(BaseItem):
    def __getitem__(self, item):
        return self._value[item]

    def __setitem__(self, key, value):
        self._value[key].set(value)

    def __len__(self):
        return len(self._value)

    def default(self, _value: List):
        self._default = _value
        self._value = self._default
        return self

    @property
    def json(self):
        _value = [i.json for i in self._value]

        value = self._json()
        value["value"] = _value
        return value


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

    @property
    def json(self):
        value = self._json()
        value.update({
            "secret": self._secret,
            "link": self._link,
            "textarea": self._textarea,
            "value": self._value,
        })
        return value


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

    @property
    def json(self):
        value = self._json()
        value.update({
            "min": self._min,
            "max": self._max,
            "step": self._step,
            "value": self._value,
        })
        return value


class BoolItem(BaseItem):
    _value: bool = None
    _default: bool = None

    def default(self, _value: bool):
        self._default = _value
        self._value = self._default
        return self

    @property
    def json(self):
        value = self._json()
        value["value"] = self._value
        return value


class SchemaManager:
    def __init__(self, path: str):
        self.path = path
        self._schema: Optional[DictItem] = None

        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8"):
                pass

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
        return yaml.dump(self._schema.json, allow_unicode=True)

    def dump(self):
        if self._schema is not None:
            with open(self.path, "w", encoding="utf-8") as fp:
                yaml.dump(self._schema.json, fp, allow_unicode=True)

    @classmethod
    def _to_schema(cls, data: Dict):
        match data["value"]:
            case list():
                result = ListItem()
                for k, v in data.items():
                    if k == "value":
                        result.__setattr__(f"_{k}", [cls._to_schema(i) for i in v])
                    else:
                        result.__setattr__(f"_{k}", v)
                return result

            case dict():
                result = DictItem()
                for k, v in data.items():
                    if k == "value":
                        result.__setattr__(f"_{k}", {k2: cls._to_schema(v2) for k2, v2 in v.items()})
                    else:
                        result.__setattr__(f"_{k}", v)
                return result

            case str():
                result = StringItem()
                for k, v in data.items():
                    result.__setattr__(f"_{k}", v)
                return result

            case bool():
                result = BoolItem()
                for k, v in data.items():
                    result.__setattr__(f"_{k}", v)
                return result

            case int():
                result = IntItem()
                for k, v in data.items():
                    result.__setattr__(f"_{k}", v)
                return result

    def load(self, schema: DictItem = None):
        if schema is None:
            with open(self.path, "r", encoding="utf-8") as fp:
                data: Dict = yaml.load(fp, yaml.FullLoader)
            if data is not None:
                self._schema = self._to_schema(data)
        else:
            self._schema = schema

    @property
    def schema(self):
        return self._schema


default_schema = SchemaManager.dict({
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
        "dev": SchemaManager.bool().default(False).description("开发模式"),
    }).description("服务器启动项"),
}).description("服务器配置文件")
