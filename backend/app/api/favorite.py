"""收藏股票API接口"""
from fastapi import APIRouter, Query
from app.models.favorite_model import FavoriteRequest
from app.service.favorite import list_favorites, add_favorite, remove_favorite

router = APIRouter(prefix="/api/favorite", tags=["favorite"])


@router.get("/list", response_model=dict)
async def list_favorites_api():
    """获取收藏股票列表"""
    return {
        "code": 200,
        "message": "Success",
        "data": list_favorites()
    }


@router.post("/add", response_model=dict)
async def add_favorite_api(req: FavoriteRequest):
    """添加收藏（重复收藏时刷新名称）"""
    item = add_favorite(code=req.code, market=req.market, name=req.name)
    return {
        "code": 200,
        "message": "Success",
        "data": item
    }


@router.delete("/remove", response_model=dict)
async def remove_favorite_api(
    code: str = Query(..., description="股票代码"),
    market: str = Query(..., description="市场类型 sh/sz")
):
    """取消收藏"""
    removed = remove_favorite(code=code, market=market)
    return {
        "code": 200,
        "message": "Success" if removed else "记录不存在",
        "data": {"removed": removed}
    }
