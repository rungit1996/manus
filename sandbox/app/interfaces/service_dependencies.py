from functools import lru_cache

from app.services.file import FileService
from app.services.shell import ShellService


@lru_cache()
def get_shell_service() -> ShellService:
    return ShellService()


@lru_cache()
def get_file_service() -> FileService:
    return FileService()
