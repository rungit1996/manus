import logging

from fastapi import APIRouter

from app.interfaces.schemas.base import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["状态模块"])


@router.get(
    path="",
    response_model=Response,
    summary="系统健康检查",
    description="检查系统的 Postgres、Redis、FastAPI 等组件的状态信息。"
)
async def get_status() -> Response:
    """系统健康检查，检查 Postgres/Redis/FastAPI/COS 等服务"""

    # todo: 等待 postgres/redis 等服务接入后补全代码

    return Response.success()
