import uuid
from typing import Any

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import SendMessageRequest, MessageSendParams


async def main() -> None:
    # 1. 定义 a2a 基础 url 地址
    base_url = "http://localhost:9999"

    # 2. 创建一个 httpx 客户端上下文
    async with httpx.AsyncClient(timeout=60) as httpx_client:
        # 3. 创建一个 Agent 卡片解析器
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        agent_card = await resolver.get_agent_card()
        print("Agent Card:", agent_card)

        # 4. 创建一个 A2A 客户端
        client = A2AClient(
            httpx_client=httpx_client,
            agent_card=agent_card
        )

        # 5. 构建发送消息载体
        send_message_payload: dict[str, Any] = {
            "message": {
                "messageId": uuid.uuid4().hex,
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "帮我随机生成10个整数"}
                ]
            }
        }

        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            params=MessageSendParams(**send_message_payload),
        )
        response = await client.send_message(request)

        print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
