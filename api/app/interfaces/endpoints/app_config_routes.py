import logging

from fastapi import APIRouter, Depends

from app.application.services.app_config_service import AppConfigService
from app.domain.models.app_config import LLMConfig, AgentConfig
from app.interfaces.schemas.base import Response
from app.interfaces.service_dependencies import get_app_config_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/app-configs", tags=["设置模块"])


@router.get(
    path="/llm",
    response_model=Response[LLMConfig],
    summary="获取 LLM 配置信息",
    description="包含 LLM 提供商的 base_url、temperature、model_name、max_tokens"
)
async def get_llm_config(
        app_config_service: AppConfigService = Depends(get_app_config_service)
) -> Response[LLMConfig]:
    """获取 LLM 配置信息"""
    llm_config = await app_config_service.get_llm_config()
    return Response.success(data=llm_config.model_dump(exclude={"api_key"}))


@router.post(
    path="/llm",
    response_model=Response[LLMConfig],
    summary="更新 LLM 配置信息",
    description="更新 LLM 配置信息，当 api_key 为空时表示不更新该字段"
)
async def update_llm_config(
        new_app_config: LLMConfig,
        app_config_service: AppConfigService = Depends(get_app_config_service)
) -> Response[LLMConfig]:
    """更新 LLM 配置信息"""
    update_llm_config = await app_config_service.update_llm_config(new_app_config)
    return Response.success(
        msg="更新 LLM 信息配置成功",
        data=update_llm_config.model_dump(exclude={"api_key"})
    )


@router.get(
    path="/agent",
    response_model=Response[AgentConfig],
    summary="获取 Agent 配置信息",
    description="包含最大迭代次数、最大重试数、最大搜索结果数"
)
async def get_agent_config(
        app_config_service: AppConfigService = Depends(get_app_config_service)
) -> Response[AgentConfig]:
    """ 获取 Agent 通用配置信息"""
    agent_config = await app_config_service.get_agent_config()
    return Response.success(data=agent_config.model_dump())


@router.post(
    path="/agent",
    response_model=Response[AgentConfig],
    summary="更新 Agent 通用配置信息",
    description="更新 Agent 通用配置信息"
)
async def update_agent_config(
        new_agent_config: AgentConfig,
        app_config_service: AppConfigService = Depends(get_app_config_service)
) -> Response[AgentConfig]:
    """更新 Agent 通用配置"""
    update_agent_config = await app_config_service.update_agent_config(new_agent_config)
    return Response.success(
        msg="更新 Agent 通用配置成功",
        data=update_agent_config.model_dump()
    )
