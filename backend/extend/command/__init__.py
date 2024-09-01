from typing import List

from pydantic import BaseModel, Field


class CommandConfig(BaseModel):
    listener: str = Field("", description="用于监听的账户")
    forums: List[str] = Field([], description="开启指令管理器的贴吧")
