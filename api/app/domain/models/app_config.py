from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LLMConfig(BaseModel):
    """语言模型配置"""
    base_url: HttpUrl = "https://api.deepseek.com"  # 基础URL地址
    api_key: str = ""  # API 密钥
    model_name: str = "deepseek-reasoner"  # 推理模型如果传递了 tools ，底层会自动切换到 deepseek-chat
    temperature: float = Field(default=0.7)  # 温度
    max_tokens: int = Field(8192, ge=0)  # 最大输出 token 数


class AppConfig(BaseModel):
    """应用配置信息，包含 Agent 配置、LLM 提供商、A2A 网络、MCP 服务配置等"""

    llm_config: LLMConfig  # 语言模型配置

    # Pydantic 配置，允许传递额外的字段初始化
    model_config = ConfigDict(extra="allow")
