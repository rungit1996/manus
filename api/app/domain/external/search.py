from typing import Protocol, Optional

from app.domain.models.search import SearchResult
from app.domain.models.tool_result import ToolResult


class SearchEngine(Protocol):
    """搜索引擎 API 接口协议"""

    async def invoke(self, query: str, date_range: Optional[str] = None) -> ToolResult[SearchResult]:
        """根据传递的 query+date_range（时间筛选）调用搜索引擎获取工具"""
        ...
