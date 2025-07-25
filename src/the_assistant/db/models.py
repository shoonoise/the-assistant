"""Database models for The Assistant."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class User(Base):
    """Application user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String)
    first_name: Mapped[str | None] = mapped_column(String)
    last_name: Mapped[str | None] = mapped_column(String)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    google_credentials_enc: Mapped[str | None] = mapped_column(Text)
    google_creds_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    google_calendar_id: Mapped[str | None] = mapped_column(String)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    settings: Mapped[list["UserSetting"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    third_party_accounts: Mapped[list["ThirdPartyAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserSetting(Base):
    """Key/value settings for a user."""

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # TODO: consider a table enumerating allowed keys
    key: Mapped[str] = mapped_column(String, nullable=False)
    value_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="settings")


class ThirdPartyAccount(Base):
    """External account credentials for a user."""

    __tablename__ = "third_party_accounts"
    __table_args__ = (UniqueConstraint("user_id", "provider", "account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    account: Mapped[str | None] = mapped_column(String)
    credentials_enc: Mapped[str | None] = mapped_column(Text)
    creds_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="third_party_accounts")
