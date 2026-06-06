"""
1. supervisor 启动后，通过一个 Unix 套接字文件来实现通信（rpc协议）
2. 连接这个通信文件，/tmp/supervisor.sock （xml-rpc连接）
3. 使用某种方式来完整转换，让 xml-rpc 实现连接 supervisor.sock
4. 连接之后我们就可以调用 rpc 对应的方法，getAllProcessInfo()
"""
import asyncio
import http.client
import logging
import socket
import threading
import xmlrpc.client
from datetime import datetime, timedelta
from typing import List, Any

from app.core.config import get_settings
from app.interfaces.errors.exceptions import BadRequestException, AppException
from app.models.supervisor import ProcessInfo, SupervisorActionResult

logger = logging.getLogger(__name__)


class UnixStreamHTTPConnection(http.client.HTTPConnection):
    """基于 Unix 流的 HTTP 连接处理器"""

    def __init__(self, host: str, socket_path: str, timeout: None) -> None:
        """构造函数，完成连接处理器初始化"""
        http.client.HTTPConnection.__init__(self, host, timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        """重写连接方法，欺骗 xml-rpc 库，让其觉得自己正在进行网络连接"""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)


class UnixStreamTransport(xmlrpc.client.Transport):
    """基于 Unix 流传输层的适配器/转换器"""

    def __init__(self, socket_path: str, timeout=30) -> None:
        """构造函数，完成传输适配器的初始化"""
        xmlrpc.client.Transport.__init__(self)
        self.socket_path = socket_path
        self.timeout = timeout

    def make_connection(self, host) -> http.client.HTTPConnection:
        return UnixStreamHTTPConnection(host, self.socket_path, self.timeout)


class SupervisorService:
    """supervisor 服务"""

    def __init__(self) -> None:
        """构造函数，完成 supervisor 服务链接"""
        # 1. 连接 supervisor 配置
        self.rpc_url = "/tmp/supervisor.sock"
        self._connect_rpc()

        # 2. supervisor 超时配置
        settings = get_settings()
        self.timeout_active = settings.server_timeout_minutes is not None
        self.shutdown_task = None
        self.shutdown_time = None
        self._expand_enabled = True  # 是否自动保活（每调用一次接口就增加时间）

        # 3. 检测是否配置了自动销毁
        if settings.server_timeout_minutes is not None:
            # 4. 设置销毁时间+定时器
            self.shutdown_time = datetime.now() + timedelta(minutes=settings.server_timeout_minutes)
            self._setup_timer(settings.server_timeout_minutes)

    @property
    def expand_enabled(self) -> bool:
        """只读属性，返回是否自动保活"""
        return self._expand_enabled

    def enable_expand(self) -> None:
        """开启自动保活"""
        self._expand_enabled = True

    def disable_expand(self) -> None:
        """关闭自动保活"""
        self._expand_enabled = False

    def _setup_timer(self, minutes: int) -> None:
        """传递时间（分钟）并创建定时器，在时间结束之后关闭 supervisord 主进程"""
        # 1. 检测当前是否存在销毁任务，如果存在则先取消
        if self.shutdown_task:
            try:
                self.shutdown_task.cancel()
            except Exception as e:
                logger.warning(f"取消 shutdown 任务失败：{str(e)}")

        # 2. 创建一个异步定时器任务函数
        async def shutdown_after_timeout():
            await asyncio.sleep(minutes * 60)
            await self.shutdown()

        try:
            # 3. 获取事件循环并添加任务
            loop = asyncio.get_event_loop()
            self.shutdown_task = loop.create_task(shutdown_after_timeout())
        except Exception as _:
            # 4. 如果事件循环失败，则创建一个新的线程来执行定时器
            if hasattr(self, "shutdown_timer") and self.shutdown_timer:
                self.shutdown_timer.cancel()
            # 5. 使用线程创建关闭定时器并设置在后台运行
            self.shutdown_timer = threading.Timer(
                minutes * 60,
                lambda: asyncio.run(self.shutdown())
            )
            self.shutdown_timer.daemon = True
            self.shutdown_timer.start()

    def _connect_rpc(self) -> None:
        """使用 python 的 xml-rpc 客户端连接一个本地 sock 文件实现连接 rpc 服务"""
        try:
            self.server = xmlrpc.client.ServerProxy(
                "http://localhost",
                transport=UnixStreamTransport(self.rpc_url),
            )
        except Exception as e:
            logger.error(f"连接 Supervisor 服务失败：{str(e)}")
            raise BadRequestException(f"连接 Supervisor 服务失败：{str(e)}")

    @classmethod
    async def _call_rpc(cls, method, *args) -> Any:
        """根据传递的方法+参数调用 rpc 方法"""
        try:
            return await asyncio.to_thread(method, *args)
        except Exception as e:
            logger.error(f"RPC 方法调用失败：{str(e)}")
            raise BadRequestException(f"RPC 方法调用失败：{str(e)}")

    async def get_all_processes(self) -> List[ProcessInfo]:
        """获取当前 supervisor 管理的所有进程信息"""
        try:
            processes = await self._call_rpc(self.server.supervisor.getAllProcessInfo)
            return [ProcessInfo(**process) for process in processes]
        except Exception as e:
            logger.error(f"获取进程信息失败： {str(e)}")
            raise AppException(f"获取进程信息失败： {str(e)}")

    async def stop_all_processes(self) -> SupervisorActionResult:
        """停止 supervisor 管理的所有进程"""
        try:
            result = await self._call_rpc(self.server.supervisor.stopAllProcesses)

            return SupervisorActionResult(
                status="stopped",
                result=result
            )
        except Exception as e:
            logger.error(f"停止 supervisor 所有进程服务失败：{str(e)}")
            raise AppException(f"停止 supervisor 所有进程服务失败：{str(e)}")

    async def shutdown(self) -> SupervisorActionResult:
        """关闭 supervisor 服务"""
        try:
            shutdown_result = await self._call_rpc(self.server.supervisor.shutdown)

            return SupervisorActionResult(
                status="shutdown",
                shutdown_result=shutdown_result
            )
        except Exception as e:
            logger.error(f"关闭 supervisor 服务失败：{str(e)}")
            raise AppException(f"关闭 supervisor 服务失败：{str(e)}")

    async def restart(self) -> SupervisorActionResult:
        """重启 supervisor 管理的进程"""
        try:
            stop_result = await self._call_rpc(self.server.supervisor.stopAllProcesses)
            start_result = await self._call_rpc(self.server.supervisor.startAllProcesses)

            return SupervisorActionResult(
                status="shutdown",
                stop_result=stop_result,
                start_result=start_result,
            )
        except Exception as e:
            logger.error(f"重启 supervisor 服务失败：{str(e)}")
            raise AppException(f"重启 supervisor 服务失败：{str(e)}")
