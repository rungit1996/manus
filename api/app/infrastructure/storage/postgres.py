import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine, AsyncSession

from core.config import get_settings

logger = logging.getLogger(__name__)


class Postgres:
    """Postgres 数据库基础类，用于完成数据库连接等配套操作"""

    def __init__(self):
        """构造函数，完成 postgres 数据库引擎、会话工厂的创建"""
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._settings = get_settings()

    async def init(self) -> None:
        """初始化 postgres 连接"""
        # 1. 判断是否已经创建好引擎，如果连上了则中断程序
        if self._engine is not None:
            logger.warning(f"Postgres 引擎已初始化，无需重复操作")
            return

        try:
            logger.info("正在初始化 Postgres 连接...")
            # 2. 创建异步引擎
            self._engine = create_async_engine(
                self._settings.sqlalchemy_database_uri,
                echo=True if self._settings.env == "development" else False,
            )

            # 3. 创建会话工厂
            self._session_factory = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
            logger.info("Postgres 会话工厂创建完毕")

            # 4. 连接 Postgres并执行预操作
            async with self._engine.begin() as async_conn:
                # 5. 检查是否安装了 uuid 扩展，如果没有的话则安装它
                await async_conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                logger.info("成功连接 Postgres 并安装 uuid-ossp 扩展")
        except Exception as e:
            logger.error(f"连接 Postgres 失败: {str(e)}")
            raise

    async def shutdown(self) -> None:
        """关闭 Postgres 连接"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("成功关闭 Postgres 连接")

        get_postgres.cache_clear()

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """只读属性，返回已初始化的会话工厂"""

        if self._session_factory is None:
            raise RuntimeError("Postgres 未初始化，请先调用 init() 函数初始化")
        return self._session_factory


@lru_cache
def get_postgres() -> Postgres:
    """使用 lru_cache 实现单例模式，获取 Postgres 实例"""
    return Postgres()


async def get_db_session() -> AsyncSession:
    """FastAPI 依赖项，用于在每个请求中异步获取数据库会话实例，确保会话在正确使用后被关闭"""
    # 1. 获取引擎和会话工厂
    db = get_postgres()
    session_factory = db.session_factory

    # 2. 创建会话上下文，在上下文内完成数据提交
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as _:
            await session.rollback()
            raise
