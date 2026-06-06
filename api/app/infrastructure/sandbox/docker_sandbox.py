import asyncio
import logging
import socket
import uuid
from typing import Optional, Self

import docker
import httpx
from async_lru import alru_cache
from docker.models.resource import Model

from app.domain.external.sandbox import Sandbox
from core.config import get_settings

logger = logging.getLogger(__name__)


class DockerSandbox(Sandbox):
    """基于 Docker 的沙箱服务"""

    def __init__(
            self,
            ip: Optional[str] = None,
            container_name: Optional[str] = None,
    ) -> None:
        """构造函数，完成 Docker 沙箱扩展创建"""
        self.client = httpx.AsyncClient(timeout=600)
        self._ip = ip
        self._container_name = container_name
        self._base_url = f"http://{ip}:8080"
        self._vnc_url = f"ws://{ip}:5901"
        self._cdp_url = f"http://{ip}:9222"

    @property
    def id(self) -> str:
        """获取沙箱的唯一 id，使用容器名字"""
        if not self._container_name:
            return "manus-sandbox"
        return self._container_name

    @property
    def vnc_url(self) -> str:
        return self._vnc_url

    @property
    def cdp_url(self) -> str:
        return self._cdp_url

    @classmethod
    async def create(cls) -> Self:
        """类方法，创建沙箱容器"""
        # 1. 获取系统配置信息
        settings = get_settings()

        # 2. 判断是否使用现成的沙箱
        if settings.sandbox_address:
            # 3. 将沙箱主机/地址解析成 ip
            ip = await cls._resolve_hostname_to_ip(settings.sandbox_address)
            return DockerSandbox(ip=ip)

        # 4. 使用子线程创建一个容器并返回
        return await asyncio.to_thread(cls._create_task)

    @classmethod
    @alru_cache(maxsize=128, typed=True)
    async def _resolve_hostname_to_ip(cls, hostname: str) -> Optional[str]:
        """将 docker 容器主机/地址转换成 ipv4 格式数据"""
        try:
            # 1. 首先判断传递的 hostname 是不是 ip
            try:
                socket.inet_pton(socket.AF_INET, hostname)
                return hostname
            except OSError:
                pass

            # 2. 使用 socket 获取地址信息
            addr_info = socket.getaddrinfo(hostname, None, family=socket.AF_INET)

            # 3. 判断地址信息是否存在，如果存在则返回第一个 ipv4 地址
            if addr_info and len(addr_info) > 0:
                return addr_info[0][4][0]
        except Exception as e:
            logger.error(f"解析 Docker 容器主机地址 {hostname} 失败：{str(e)}")
            return None

    @classmethod
    def _get_container_ip(cls, container: Model) -> str:
        """根据传递的容器，获取 ip 信息"""
        # 1. 获取 inspect 网络设置
        network_settings = container.attrs["NetworkSettings"]
        ip_address = network_settings["IPAddress"]

        # 2. 判断容器是否存在 ip，如果不存在则从 networks 中获取
        if not ip_address and "Networks" in network_settings:
            networks = network_settings["Networks"]
            # 3. 循环遍历每一项网络配置
            for network_name, network_config in networks.items():
                if "IPAddress" in network_config and network_config["IPAddress"]:
                    ip_address = network_config["IPAddress"]
                    break

        return ip_address

    @classmethod
    def _create_task(cls) -> Self:
        """创建沙箱容器的异步任务"""
        # 1. 获取系统配置信息
        settings = get_settings()

        # 2. 构建容器的名字
        image = settings.sandbox_image
        name_prefix = settings.sandbox_name_prefix
        container_name = f"{name_prefix}--{str(uuid.uuid4())[:8]}"

        try:
            # 3. 创建一个 docker 客户端
            client = docker.from_env()

            # 4. 预配置容器信息
            container_config = {
                "image": image,
                "name": container_name,
                "detach": True,
                "remove": True,
                "environment": {
                    "SERVICE_TIMEOUT_MINUTES": settings.sandbox_ttl_minutes,
                    "CHROME_ARGS": settings.sandbox_chrome_args,
                    "HTTPS_PROXY": settings.sandbox_https_proxy,
                    "HTTP_PROXY": settings.sandbox_http_proxy,
                    "NO_PROXY": settings.sandbox_no_proxy,
                }
            }

            # 5. 判断是否传递了网络
            if settings.sandbox_network:
                container_config["network"] = settings.sandbox_network

            # 6. 调用 docker 客户端容器运行参数创建沙箱
            container = client.containers.run(**container_config)

            # 7. 重载并刷新容器信息
            container.reload()
            ip = cls._get_container_ip(container)

            return DockerSandbox(ip=ip, container_name=container_name)
        except Exception as e:
            logger.error(f"创建 Docker 沙箱容器失败：{str(e)}")
            raise Exception(f"创建 Docker 沙箱容器失败：{str(e)}")
