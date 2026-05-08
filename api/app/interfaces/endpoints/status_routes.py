import logging
from typing import List

from fastapi import APIRouter, Depends

from app.application.services.status_service import StatusService
from app.domain.models.health_status import HealthStatus
from app.interfaces.schemas.base import Response
from app.interfaces.service_dependencies import get_status_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["状态模块"])


@router.get(
    path="",
    response_model=Response[List[HealthStatus]],  # 接口响应格式声明
    summary="系统健康检查",
    description="检查系统的 Postgres、Redis、FastAPI 等组件的状态信息。"
)
async def get_status(
        status_service: StatusService = Depends(get_status_service)
) -> Response:
    """系统健康检查，检查 Postgres/Redis/FastAPI/COS 等服务"""
    statuses = await status_service.check_all()
    if any(item.status == "error" for item in statuses):
        return Response.fail(503, "系统服务存在异常", statuses)

    return Response.success(msg="系统健康检查成功", data=statuses)
