import os.path

from fastapi import APIRouter, Depends

from app.interfaces.errors.exceptions import BadRequestException
from app.interfaces.schemas.base import Response
from app.interfaces.schemas.shell import ExecCommandRequest
from app.interfaces.service_dependencies import get_shell_service
from app.models.shell import ShellExecResult, ShellViewResult, ViewShellRequest, ShellWaitResult, WaitForProcessRequest
from app.services.shell import ShellService

router = APIRouter(prefix="/shell", tags=["Shell模块"])


@router.post(
    path="/exec-command",
    response_model=Response[ShellExecResult],
)
async def exec_command(
        request: ExecCommandRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellExecResult]:
    """在指定的 Shell 会话中运行命令"""
    # 1. 判断下是否传递了 session_id，如果不存在则新建一个 session_id
    if not request.session_id or request.session_id == "":
        request.session_id = shell_service.create_session_id()

    # 2. 判断下是否传递了执行目录，如果未传递则使用根目录作为执行路径
    if not request.exec_dir or request.exec_dir == "":
        request.exec_dir = os.path.expanduser("~")

    # 3. 调用服务执行命令获取结果
    result = await shell_service.exec_command(
        session_id=request.session_id,
        exec_dir=request.exec_dir,
        command=request.command,
    )

    return Response.success(data=result)


@router.post(
    path="/view-shell",
    response_model=Response[ShellViewResult],
)
async def view_shell(
        request: ViewShellRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellViewResult]:
    """根据传递的会话id+是否返回控制台标识获取 Shell 命令执行结果"""
    # 1. 判断下 Shell 会话 id 是否存在
    if not request.session_id or request.session_id == "":
        raise BadRequestException("Shell 会话 id 为空，请核实后重试")

    # 2. 调用服务获取命令执行结果
    result = await shell_service.view_shell(request.session_id, request.console)

    return Response.success(data=result)


@router.post(
    path="/wait-for-process",
    response_model=Response[ShellWaitResult]
)
async def wait_for_process(
        request: WaitForProcessRequest,
        shell_service: ShellService = Depends(get_shell_service),
) -> Response[ShellWaitResult]:
    """传递会话id+描述执行等待并获取等待结果"""
    result = await shell_service.wait_for_process(request.session_id, request.seconds)

    return Response.success(
        msg=f"进程结束，返回状态码（returncode）：{result.returncode}",
        data=result,
    )
