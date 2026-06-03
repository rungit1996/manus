from typing import Optional

from pydantic import BaseModel, Field


class ReadFileRequest(BaseModel):
    """读取文件请求结构体"""
    filepath: str = Field(..., description="要读取的文件路径")
    start_line: Optional[int] = Field(default=None, description="（可选）读取的起始行，索引从 0 开始")
    end_line: Optional[int] = Field(default=None, description="（可选）结束行号，不包含该行")
    sudo: Optional[bool] = Field(default=False, description="（可选）是否使用 sudo 权限")
    max_length: Optional[int] = Field(default=1000, description="（可选）要返回的内容最大长度")
