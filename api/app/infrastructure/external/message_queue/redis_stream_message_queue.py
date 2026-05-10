import asyncio
import logging
import uuid
from typing import Any, Tuple, Optional

from app.domain.external.message_queue import MessageQueue
from app.infrastructure.storage.redis import get_redis

logger = logging.getLogger()


class RedisStreamMessageQueue(MessageQueue):
    """基于 RedisStream 的消息队列"""

    def __init__(self, stream_name: str) -> None:
        """构造函数，完成 Redis-Stream 的初始化，涵盖名字，锁的时间"""
        self._stream_name = stream_name
        self._redis = get_redis()
        self._lock_expire_seconds = 10

    async def _acquire_lock(self, lock_key: str, timeout_seconds: int = 5) -> Optional[str]:
        """根据传递的 lock 键构建一个分布式锁"""
        # 1. 创建锁对应的值
        lock_value = str(uuid.uuid4())
        end_time = timeout_seconds

        # 2. 使用 end_time 构建一个循环
        while end_time > 0:
            # 3. 使用 redis 的 set 方法，将 lock_key 和 lock_value 存储到 redis 中，并且设置过期时间
            result = await self._redis.client.set(
                lock_key,
                lock_value,
                nx=True,  # 如果值存在则设置，否则不设置
                ex=self._lock_expire_seconds
            )

            # 4. 如果设置成功呢，则返回锁的值
            if result:
                return lock_value

            # 5. 睡眠指定时间并将 end_time 递减 0.1 秒后再尝试执行设置方法
            await asyncio.sleep(0.1)
            end_time -= 0.1

        # 超时直接返回 None
        return None

    async def _release_lock(self, lock_key: str, lock_value: str) -> bool:
        """根据传递的 lock_str 和 lock_value 释放分布式锁"""
        # 1. 构建一段 redis 的脚本用于释放分布式锁
        release_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """

        try:
            # 2. 注册脚本
            script = self._redis.client.register_script(release_script)

            # 3. 执行脚本并传递 keys + args 释放分布式锁
            result = await script(keys=[lock_key], args=[lock_value])
            return result == 1
        except Exception:
            return False

    async def put(self, message: Any) -> str:
        """往 redis-stream中添加一条消息"""
        logger.debug(f"往消息队列[{self._stream_name}]中添加一条消息：{message}")
        return await self._redis.client.xadd(self._stream_name, {"data": message})

    async def get(self, start_id: str = None, block_ms: int = None) -> Tuple[str, Any]:
        """从 redis-stream 中获取一条消息"""
        logger.debug(f"从消息队列[{self._stream_name}]中获取一条消息: {start_id}")

        # 1. 判断 start_id 是否为 None
        if start_id is None:
            start_id = '0'

        # 2. 从 redis 流中获取一条数据
        messages = await self._redis.client.xread(
            {self._stream_name: start_id},
            count=1,
            block=block_ms,
        )

        # 3. 检查 messages 是否存在
        if not messages:
            return None, None

        # 4. 从消息列表中取出对应的消息数据
        stream_messages = messages[0][1]
        if not stream_messages:
            return None, None

        # 5. 提取 id 和数据
        messages_id, messages_data = stream_messages[0]

        try:
            return messages_id, messages_data.get("data")
        except Exception as e:
            logger.error(f"从消息队列[{self._stream_name}]中获取数据失败：{str(e)}")
            return None, None

    async def pop(self) -> Tuple[str, None]:
        """从消息队列中获取第一条消息并删除"""
        # 1. 记录日志
        logger.debug(f"从消息队列[{self._stream_name}]中弹出第一条消息")
        lock_key = f"lock:{self._stream_name}:pop"

        # 2. 构建分布式锁，如果分布式锁创建失败则返回 None
        lock_value = await self._acquire_lock(lock_key)
        if not lock_value:
            return None, None

        try:
            # 3. 从 redis 流中获取第一条消息
            messages = await self._redis.client.xrange(self._stream_name, '-', '+', count=1)
            if not messages:
                return None, None

            # 4. 取出消息 id 和消息
            message_id, message_data = messages[0]

            # 5. 删除消息队列中的 message 数据
            await self._redis.client.xdel(self._stream_name, message_id)

            # 6. 返回 删除的消息 id 和消息
            return message_id, message_data.get("data")

        except Exception as e:
            logger.error(f"解析消息队列[{self._stream_name}]出错：{str(e)}")
            return None, None
        finally:
            # 释放锁
            await self._release_lock(lock_key, lock_value)

    async def clear(self) -> None:
        """清除 redis-stream 中的所有消息"""
        await self._redis.client.xtrim(self._stream_name, 0)

    async def is_empty(self) -> bool:
        """检查 redis-stream 是否为空"""
        return await self.size() == 0

    async def size(self) -> int:
        """获取 redis-stream 的长度"""
        return await self._redis.client.xlen(self._stream_name)

    async def delete_message(self, message_id: str) -> bool:
        """根据传递的消息 id 从 redis-stream 中删除指定消息"""
        try:
            await self._redis.client.xdel(self._stream_name, message_id)
            return True
        except Exception:
            return False
