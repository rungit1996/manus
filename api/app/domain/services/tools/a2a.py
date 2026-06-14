import logging

logger = logging.getLogger(__name__)

"""
A2A 客户端管理器的开发思路：
1. 在 Agent 执行过程中，有可能需要多次调用 Remote-Agent，
    但是 a2a 中的 agent-card.json 请求是网络 io，相对耗时
    所以需要缓存 agent-card 的相关信息，只有在初始化 A2A 客户端的时候才初始化一次，
    更新 a2a 服务器的时候更新，清除 a2a 客户端管理器时删除；
2. 在前端 UI 交互中，无论 A2A 服务器是否启动，都会展示 Card 信息，
    但是，在执行/规划 Agent 中，我们只传递启用的 A2A 服务，所以 A2A 客户端管理器必须动态接受配置；
3. 一个 A2A 客户端会同时管理多个 Agent，但是不同的 A2A 服务有可能他们的 name 是一样的，
    需要考虑传递给 Agent 信息时的唯一性，会配置多一个唯一的 id；
4. 由于使用 httpx 客户端，这个客户端需要创建上下文/释放资源，所以可以使用 AsyncExitStack 来管理异步上下文，
    避免大量使用 with..as 的嵌套组合；
5. A2AClientManager 的初始化非常耗时，一次请求中只初始化一次；
6. A2A 配置是写在 config.yaml 中的，并直接暴露给开发者，有可能开发者会手动修改 config.yaml，
    所以在使用的时候，最多需要做多一次校验
7. A2A 客户端管理器只实现两个方法，get_remote_agent_cards and call_remote_agent
8. A2A 客户端管理器停止时必须清除对应资源，涵盖了缓存，异步上下文管理器避免资源泄露；
"""
