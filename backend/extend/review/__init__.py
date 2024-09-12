from typing import List

from pydantic import BaseModel, Field

from .reviewer import Reviewer


class ReviewConfig(BaseModel):
    dev: bool = Field(False, description="只审查不执行操作")
    forums: List["ReviewForum"] = Field([], description="启用审查的吧")
    keywords: List[str] = Field([], description="需要检查的关键词")
    keyword_level: int = Field(1, description="关键词检查的最高等级", ge=1, le=18)
    level_wall: int = Field(1, description="等级墙的等级", ge=1, le=18)


class ReviewForum(BaseModel):
    name: str = Field(..., description="吧名")
    user_id: int = Field(..., description="用户id")
    functions: List[str] = Field(..., description="启用的方法")
