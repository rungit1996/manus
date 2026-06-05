from fastapi import APIRouter, Depends
from typing import List

from app.interfaces.schemas.base import Response
from app.interfaces.service_dependencies import get_supervisor_service
from app.models.supervisor import ProcessInfo
from app.services.supervisor import SupervisorService

router = APIRouter(prefix="/supervisor", tags=["Supervisor模块"])


@router.get(
    path="/status",
    response_model=Response[List[ProcessInfo]],
)
async def get_status(
        supervisor_service: SupervisorService = Depends(get_supervisor_service),
) -> Response[List[ProcessInfo]]:
    """获取沙箱中所有进程服务的状态信息"""
    processes = await supervisor_service.get_all_processes()

    return Response(
        msg="获取沙箱所有进程服务信息",
        data=processes,
    )
