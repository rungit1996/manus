import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    创建一个可供所有测试用例使用的 TestClient 客户端
    scope="session" 表示 fixture 在整个测试用例只会实例化一次，可提高效率
    """
    with TestClient(app) as c:
        yield c
   