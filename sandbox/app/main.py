import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.interfaces.endpoints.routes import router
from app.interfaces.errors.exception_handlers import register_exception_handlers


def setup_logging() -> None:
    """设置沙箱 API 应用日志"""
    # 1. 获取项目配置
    settings = get_settings()

    # 2. 获取根日志处理器
    root_logger = logging.getLogger()

    # 3. 设置根日志处理器等级
    log_level = getattr(logging, settings.log_level)
    root_logger.setLevel(log_level)

    # 4. 日志输出格式定义
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 5. 创建控制台日志输出处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # 6. 将控制台日志处理器添加到根处理器中
    root_logger.addHandler(console_handler)

    root_logger.info("沙箱系统日志模块初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期上下文管理"""
    # 1. 应用开始运行之前的操作
    logger.info("Manus 沙箱正在初始化")

    try:
        # 2. lifespan 关键节点
        yield
    finally:
        # 3. 应用结束后的操作
        logger.info("Manus 沙箱关闭成功")


# 1. 初始化日志系统
setup_logging()
logger = logging.getLogger(__name__)

# 2. 定义 FastAPI 路由 tags 标签
openapi_tags = [
    {
        "name": "文件模块",
        "description": "包含 **文件增删改查** 等 API 接口，用于实现对沙箱文件的操作",
    },
    {
        "name": "Shell 模块",
        "description": "包含 **执行/查看 Shell** 等 API 接口，用于实现操控沙箱内部的 Shell 命令",
    },
    {
        "name": "Supervisor 模块",
        "description": "使用接口+Supervisor 实现管理沙箱系统的程序逻辑",
    },
]

# 3. 实例化 FastAPI 项目实例
app = FastAPI(
    title="Manus 沙箱系统",
    description="该沙箱系统中预装了 Chrome、Python、Node.js，支持运行 Shell 命令、文件管理等",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
    version="1.0.0",
)

# 4. 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 5. 注册错误并处理
register_exception_handlers(app)

# 6. 集成路由
app.include_router(router, prefix="/api")
