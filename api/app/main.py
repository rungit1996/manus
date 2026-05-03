import sys

print("sys.path", sys.path)
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.logging import setup_logging
from app.infrastructure.storage.redis import get_redis
from app.infrastructure.storage.postgres import get_postgres
from app.infrastructure.storage.cos import get_cos
from app.interfaces.endpoints.routers import router
from app.interfaces.errors.exception_handlers import register_exception_handlers
from core.config import get_settings

# 1. 加载配置信息
settings = get_settings()

# 2. 初始化日志系统
setup_logging()
logger = logging.getLogger()

# logger.info("测试日志系统")

# 3. 定义 FastAPI 路由 tags 标签
openapi_tags = [
    {
        "name": "状态模块",
        "description": "包含 **状态监测** 等 API 接口，用于监测系统的运行状态"
    }
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """创建 FastAPI 应用程序生命周期上下文管理"""

    # 打印日志表示程序开始了
    logger.info("Manus 正在初始化")

    # 初始化 Redis 缓存客户端、 Postgres 业务客户端、Cos 存储客户端
    await get_redis().init()
    await get_postgres().init()
    await get_cos().init()

    try:
        # lifespan 节点/分界
        yield
    finally:
        await get_redis().shutdown()
        await get_postgres().shutdown()
        await get_cos().shutdown()
        logger.info("Manus 正在关闭")


# print(settings)

# 4. 创建 Manus 应用实例
# uv run uvicorn app.main:app --reload --lifespan on
app = FastAPI(
    title="Manus通用智能体",
    description="Manus 是一个通用的 AI Agent 系统，可以完全私有化部署，使用 A2A+MCP 连接 Agent/Tool，同时支持在沙箱中运行各种内置工具和操作。",
    lifespan=lifespan,
    openapi_tags=openapi_tags,
    version="1.0.0"
)

# 5. 配置 CORS 中间件，解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]

)

# 6. 注册错误处理器
register_exception_handlers(app)

# 7. 集成路由
app.include_router(router, prefix="/api")
