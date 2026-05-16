from typing import Optional, List

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """搜索结果条目数据类型"""
    url: str  # 搜索条目 URL 链接
    title: str  # 搜索条目标题
    snippet: str = ""  # 搜索条目摘要信息


class SearchResult(BaseModel):
    """搜索结果数据模型"""
    query: str  # 查询 query
    date_range: Optional[str] = None  # 搜索日期范围
    total_results: int = 0  # 搜索结果条数
    results: List[SearchResultItem] = Field(default_factory=list)  # 搜索结果
