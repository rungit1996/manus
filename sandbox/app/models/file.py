from pydantic import BaseModel, Field


class FileReadResult(BaseModel):
    """文件读取结果"""
    filepath: str = Field(..., description="要读取的文件路径")
    content: str = Field(..., description="读取的文件内容")
