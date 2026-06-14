import uuid
from typing import List

from app.application.errors.exceptions import NotFoundError
from app.domain.models.app_config import AppConfig, LLMConfig, AgentConfig, MCPConfig, A2AConfig, A2AServerConfig
from app.domain.repositories.app_config_repositories import AppConfigRepository
from app.domain.services.tools.a2a import A2AClientManager
from app.domain.services.tools.mcp import MCPClientManager
from app.interfaces.schemas.app_config import ListMCPServerItem, ListA2AServerItem


class AppConfigService:
    """应用配置服务"""

    def __init__(self, app_config_repository: AppConfigRepository):
        """构造函数，完成应用配置服务的初始化"""
        self.app_config_repository = app_config_repository

    async def _load_app_config(self) -> AppConfig:
        """加载获取所有的应用配置"""
        return self.app_config_repository.load()

    async def get_llm_config(self) -> LLMConfig:
        """获取 LLM 提供商配置"""
        app_config = await self._load_app_config()
        return app_config.llm_config

    async def update_llm_config(self, llm_config: LLMConfig) -> LLMConfig:
        """根据传递的 llm_config 更新语言模型提供商配置"""
        # 1. 获取应用配置
        app_config = await self._load_app_config()

        # 2. 判断 api_key 是否为空
        if not llm_config.api_key.strip():
            llm_config.api_key = app_config.llm_config.api_key

        # 3. 调用函数更新 app_config
        app_config.llm_config = llm_config
        self.app_config_repository.save(app_config)

        return app_config.llm_config

    async def get_agent_config(self) -> AgentConfig:
        """获取 Agent 通用配置"""
        app_config = await self._load_app_config()
        return app_config.agent_config

    async def get_mcp_servers(self) -> List[ListMCPServerItem]:
        """获取 MCP 服务器列表"""
        # 1. 获取当前应用配置
        app_config = await self._load_app_config()

        # 2. 创建 mcp 客户端管理，对配置信息不进行过滤
        mcp_servers = []
        mcp_client_manager = MCPClientManager(mcp_config=app_config.mcp_config)

        try:
            # 3. 初始化 mcp 客户端管理器
            await mcp_client_manager.initialize()

            # 4. 获取 mcp 客户端管理器的工具列表
            tools = mcp_client_manager.tools

            # 5. 循环组装响应的工具格式
            for server_name, server_config in app_config.mcp_config.mcpServers.items():
                mcp_servers.append(ListMCPServerItem(
                    server_name=server_name,
                    ennabled=server_config.enabled,
                    transport=server_config.transport,
                    tools=[tool.name for tool in tools.get(server_name, [])]
                ))
        finally:
            # 清除 MCP 客户端管理器的相关资源
            await mcp_client_manager.cleanup()

        return mcp_servers

    async def update_agent_config(self, agent_config: AgentConfig) -> AgentConfig:
        """根据传递的 agent_config 更新 Agent 通用配置信息"""
        app_config = await self._load_app_config()

        app_config.agent_config = agent_config
        self.app_config_repository.save(app_config)

        return app_config.agent_config

    async def update_and_create_mcp_servers(self, mcp_config: MCPConfig) -> MCPConfig:
        """根据传递的数据新增或更新 MCP 配置"""
        # 1. 获取应用配置信息
        app_config = await self._load_app_config()

        # 2. 使用新的 mcp_config 更新原始的配置
        app_config.mcp_config.mcpServers.update(mcp_config.mcpServers)

        # 3. 调用数据仓库完成存储 or 更新
        self.app_config_repository.save(app_config)

        return app_config.mcp_config

    async def delete_mcp_server(self, server_name: str) -> MCPConfig:
        """根据名字删除 MCP 服务"""
        # 1. 获取应用配置信息
        app_config = await self._load_app_config()

        # 2. 查询对应服务的名字是否存在
        if server_name not in app_config.mcp_config.mcpServers:
            raise NotFoundError(f"该 MCP 服务[{server_name}]不存在，请核实之后重试")

        # 3. 如果存在则删除字典中对应的服务
        del app_config.mcp_config.mcpServers[server_name]

        self.app_config_repository.save(app_config)

        return app_config.mcp_config

    async def set_mcp_server_enabled(self, server_name: str, enabled: bool) -> MCPConfig:
        """更新 MCP 服务启用状态"""

        # 1. 获取应用配置信息
        app_config = await self._load_app_config()

        # 2. 查询对应服务的名字是否存在
        if server_name not in app_config.mcp_config.mcpServers:
            raise NotFoundError(f"该 MCP 服务[{server_name}]不存在，请核实之后重试")

        # 3. 如果存在则更新服务的启用状态
        app_config.mcp_config.mcpServers[server_name].enabled = enabled

        self.app_config_repository.save(app_config)

        return app_config.mcp_config

    async def create_a2a_server(self, base_url: str) -> A2AConfig:
        """根据传递的配置新增 a2a 服务器"""
        # 1. 获取当前的应用配置
        app_config = await self._load_app_config()

        # 2. 往数据中新增 a2a 服务（在新增之前其实可以检测下当前 agent 是否存在）
        a2a_server_config = A2AServerConfig(
            id=str(uuid.uuid4()),
            base_url=base_url,
            enabled=True,
        )
        app_config.a2a_config.a2a_servers.append(a2a_server_config)

        # 3. 调用数据仓库更新
        self.app_config_repository.save(app_config)

        return app_config.a2a_config

    async def get_a2a_servers(self) -> List[ListA2AServerItem]:
        """获取 A2A 服务列表"""
        # 1. 获取当前的应用配置
        app_config = await self._load_app_config()

        # 2. 构建 A2A 客户端管理器，对配置信息不过滤
        a2a_servers = []
        a2a_client_manager = A2AClientManager(app_config.a2a_config)

        try:
            # 3. 初始化 A2A 客户端管理器
            await a2a_client_manager.initialize()

            # 4. 获取 Agent 卡片列表
            agent_cards = a2a_client_manager.agent_cards

            # 5. 组装响应结构
            for id, agent_card in agent_cards.items():
                a2a_servers.append(ListA2AServerItem(
                    id=id,
                    name=agent_card.get("name", ""),
                    description=agent_card.get("description", ""),
                    input_modes=agent_card.get("defaultInputModes", []),
                    output_modes=agent_card.get("defaultOutputModes", []),
                    streaming=agent_card.get("capabilities", {}).get("streaming", False),
                    push_notifications=agent_card.get("capabilities", {}).get("push_notifications", False),
                    enabled=agent_card.get("enabled", False),
                ))
        finally:
            # 6. 清除客户端管理器资源
            await a2a_client_manager.cleanup()

        return a2a_servers
