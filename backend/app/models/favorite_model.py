"""收藏股票相关 Pydantic 模型"""
from pydantic import BaseModel, Field


class FavoriteRequest(BaseModel):
    """添加收藏请求体"""
    code: str = Field(..., description="股票代码")
    market: str = Field(..., description="市场类型 sh/sz")
    name: str = Field(..., description="股票名称")
