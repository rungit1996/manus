import uuid

from openai import BaseModel
from pydantic import Field


class File(BaseModel):
    """文件信息 Domain 模型，用于记录 manus/human 上传 or 生成的文件"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # 文件 ID
    filename: str = ""  # 文件名字
    filepath: str = ""  # 文件路径
    key: str = ""  # 腾讯云 cos 中的路径
    extension: str = ""  # 扩展名
    mime_type: str = ""  # mine-type 类型
    size: int = 0  # 文件大小，单位是字节
