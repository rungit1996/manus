from functools import lru_cache

from app.services.shell import ShellService


@lru_cache()
def get_shell_service() -> ShellService:
    return ShellService()
