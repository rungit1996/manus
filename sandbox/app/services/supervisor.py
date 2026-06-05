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
import xmlrpc.client
from typing import List, Any

from app.interfaces.errors.exceptions import BadRequestException, AppException
from app.models.supervisor import ProcessInfo

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
        self.rpc_url = "/tmp/supervisor.sock"
        self._connect_rpc()

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
