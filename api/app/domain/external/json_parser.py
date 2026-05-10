from typing import Optional, Any, Union, Dict, List

from websockets import Protocol


class JSONParser(Protocol):
    """JSON 解析器，用于解析 json 字符串并修复"""

    async def invoke(self, text: str, default_value: Optional[Any] = None) -> Union[Dict, List, Any]:
        """调用函数，用于将传递的文本进行解析并返回"""
        ...
