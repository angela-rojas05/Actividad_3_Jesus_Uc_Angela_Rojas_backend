from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True
    )

    tax_id: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        unique=True
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False
    )

    company_users: Mapped[list["CompanyUser"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False
    )

    companies: Mapped[list["CompanyUser"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class CompanyUser(Base):
    __tablename__ = "company_users"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "user_id",
            name="uq_company_user"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False
    )

    company: Mapped["Company"] = relationship(
        back_populates="company_users"
    )

    user: Mapped["User"] = relationship(
        back_populates="companies"
    )

    roles: Mapped[list["CompanyUserRoleModel"]] = relationship(
        back_populates="company_user",
        cascade="all, delete-orphan"
    )


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    role_permissions: Mapped[list["RolePermissionModel"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan"
    )

    company_user_roles: Mapped[list["CompanyUserRoleModel"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan"
    )


class PermissionModel(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    role_permissions: Mapped[list["RolePermissionModel"]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan"
    )


class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permission"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "roles.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    role: Mapped["RoleModel"] = relationship(
        back_populates="role_permissions"
    )

    permission: Mapped["PermissionModel"] = relationship(
        back_populates="role_permissions"
    )


class CompanyUserRoleModel(Base):
    __tablename__ = "company_user_roles"

    __table_args__ = (
        UniqueConstraint(
            "company_user_id",
            "role_id",
            name="uq_company_user_role"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    company_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "company_users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey(
            "roles.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    company_user: Mapped["CompanyUser"] = relationship(
        back_populates="roles"
    )

    role: Mapped["RoleModel"] = relationship(
        back_populates="company_user_roles"
    )

