import uuid
from datetime import datetime

from sqlalchemy import PrimaryKeyConstraint, UUID, text, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


# alembic revision --autogenerate -m "create sessions table"

class Demo(Base):
    """Demo 模型，用于演示 alembic 数据库迁移"""
    __tablename__ = "demos"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_demos_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        nullable=False,
        primary_key=True,
        server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, server_default=text("''::character varying"))
    avatar: Mapped[str] = mapped_column(String(255), nullable=False, server_default=text("''::character varying"))
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''::text"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=datetime.now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        comment="创建时间"
    )
