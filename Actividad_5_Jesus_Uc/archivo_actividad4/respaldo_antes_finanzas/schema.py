from datetime import datetime
from typing import Optional

import strawberry

from graphql import GraphQLError
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from strawberry.schema.config import StrawberryConfig

from app.database import SessionLocal
from app.models import Company, CompanyUser, User
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


email_adapter = TypeAdapter(EmailStr)


# =========================================================
# VALIDACIONES
# =========================================================

def normalize_email(value: str) -> str:
    try:
        email = email_adapter.validate_python(value)
        return str(email).lower()

    except ValidationError as exc:
        raise GraphQLError(
            "El correo electrónico no es válido."
        ) from exc


def clean_required_text(
    value: str,
    field_name: str
) -> str:

    value = value.strip()

    if not value:
        raise GraphQLError(
            f"{field_name} es obligatorio."
        )

    return value


# =========================================================
# AUTENTICACIÓN
# =========================================================

def get_authenticated_user_id(
    info: strawberry.Info
) -> int:

    request = info.context["request"]

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith("Bearer "):
        raise GraphQLError(
            "Debes autenticarte con un token Bearer."
        )

    token = authorization.removeprefix(
        "Bearer "
    ).strip()

    try:
        return decode_access_token(token)

    except ValueError as exc:
        raise GraphQLError(
            str(exc)
        ) from exc


def ensure_company_admin(
    info: strawberry.Info,
    company_id: int
) -> None:

    user_id = get_authenticated_user_id(info)

    with SessionLocal() as db:

        user = db.get(
            User,
            user_id
        )

        if user is None or not user.is_active:
            raise GraphQLError(
                "Usuario autenticado no válido o inactivo."
            )

        relation = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == user_id,
                CompanyUser.is_admin.is_(True),
                CompanyUser.is_active.is_(True),
            )
        )

        if relation is None:
            raise GraphQLError(
                "Solo el administrador de la empresa "
                "puede registrar usuarios."
            )


# =========================================================
# TIPOS GRAPHQL
# =========================================================

@strawberry.type(name="Company")
class CompanyType:
    id: strawberry.ID
    name: str
    legal_name: Optional[str]
    tax_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type(name="User")
class UserType:
    id: strawberry.ID
    name: str
    email: str
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type(name="CompanyUser")
class CompanyUserType:
    id: strawberry.ID
    company_id: strawberry.ID
    user_id: strawberry.ID
    is_admin: bool
    is_active: bool
    joined_at: datetime
    company: CompanyType
    user: UserType


@strawberry.type
class AuthUser:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class AuthPayload:
    token: str
    token_type: str
    user: AuthUser


# =========================================================
# INPUTS
# =========================================================

@strawberry.input
class CreateCompanyInput:
    name: str
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


@strawberry.input
class UpdateCompanyInput:
    id: strawberry.ID
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class CreateCompanyAdminInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


@strawberry.input
class CreateCompanyUserInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


# =========================================================
# CONVERSIÓN MODELO -> GRAPHQL
# =========================================================

def company_to_type(
    company: Company
) -> CompanyType:

    return CompanyType(
        id=strawberry.ID(str(company.id)),
        name=company.name,
        legal_name=company.legal_name,
        tax_id=company.tax_id,
        email=company.email,
        phone=company.phone,
        is_active=company.is_active,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def user_to_type(
    user: User
) -> UserType:

    return UserType(
        id=strawberry.ID(str(user.id)),
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def company_user_to_type(
    company_user: CompanyUser
) -> CompanyUserType:

    return CompanyUserType(
        id=strawberry.ID(
            str(company_user.id)
        ),

        company_id=strawberry.ID(
            str(company_user.company_id)
        ),

        user_id=strawberry.ID(
            str(company_user.user_id)
        ),

        is_admin=company_user.is_admin,
        is_active=company_user.is_active,
        joined_at=company_user.joined_at,

        company=company_to_type(
            company_user.company
        ),

        user=user_to_type(
            company_user.user
        ),
    )


# =========================================================
# QUERIES
# =========================================================

@strawberry.type
class Query:

    @strawberry.field
    def companies(
        self,
        active_only: Optional[bool] = None
    ) -> list[CompanyType]:

        with SessionLocal() as db:

            stmt = select(
                Company
            ).order_by(
                Company.id
            )

            if active_only is True:
                stmt = stmt.where(
                    Company.is_active.is_(True)
                )

            companies = db.scalars(
                stmt
            ).all()

            return [
                company_to_type(company)
                for company in companies
            ]


    @strawberry.field
    def company(
        self,
        id: strawberry.ID
    ) -> Optional[CompanyType]:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(id)
            )

            if company is None:
                return None

            return company_to_type(
                company
            )


    @strawberry.field
    def company_users(
        self,
        company_id: strawberry.ID
    ) -> list[CompanyUserType]:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(company_id)
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            stmt = (
                select(CompanyUser)
                .where(
                    CompanyUser.company_id
                    == int(company_id)
                )
                .order_by(
                    CompanyUser.id
                )
            )

            relations = db.scalars(
                stmt
            ).all()

            return [
                company_user_to_type(relation)
                for relation in relations
            ]


# =========================================================
# MUTATIONS
# =========================================================

@strawberry.type
class Mutation:

    # -----------------------------------------------------
    # CREAR EMPRESA
    # -----------------------------------------------------

    @strawberry.mutation
    def create_company(
        self,
        input: CreateCompanyInput
    ) -> CompanyType:

        with SessionLocal() as db:

            email = (
                normalize_email(input.email)
                if input.email
                else None
            )

            tax_id = (
                input.tax_id.strip().upper()
                if input.tax_id
                else None
            )

            if tax_id:

                existing_tax = db.scalar(
                    select(Company).where(
                        Company.tax_id == tax_id
                    )
                )

                if existing_tax:
                    raise GraphQLError(
                        "El taxId ya está registrado."
                    )

            company = Company(
                name=clean_required_text(
                    input.name,
                    "El nombre"
                ),

                legal_name=(
                    input.legal_name.strip()
                    if input.legal_name
                    else None
                ),

                tax_id=tax_id,
                email=email,

                phone=(
                    input.phone.strip()
                    if input.phone
                    else None
                ),
            )

            db.add(company)
            db.commit()
            db.refresh(company)

            return company_to_type(
                company
            )


    # -----------------------------------------------------
    # ACTUALIZAR EMPRESA
    # -----------------------------------------------------

    @strawberry.mutation
    def update_company(
        self,
        input: UpdateCompanyInput
    ) -> CompanyType:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(input.id)
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if input.name is not None:

                company.name = clean_required_text(
                    input.name,
                    "El nombre"
                )

            if input.legal_name is not None:

                company.legal_name = (
                    input.legal_name.strip()
                    or None
                )

            if input.tax_id is not None:

                new_tax_id = (
                    input.tax_id.strip().upper()
                    or None
                )

                if new_tax_id:

                    existing = db.scalar(
                        select(Company).where(
                            Company.tax_id == new_tax_id,
                            Company.id != company.id
                        )
                    )

                    if existing:
                        raise GraphQLError(
                            "El taxId ya está registrado."
                        )

                company.tax_id = new_tax_id

            if input.email is not None:

                company.email = (
                    normalize_email(input.email)
                    if input.email.strip()
                    else None
                )

            if input.phone is not None:

                company.phone = (
                    input.phone.strip()
                    or None
                )

            if input.is_active is not None:

                company.is_active = (
                    input.is_active
                )

            db.commit()
            db.refresh(company)

            return company_to_type(
                company
            )


    # -----------------------------------------------------
    # DESACTIVAR EMPRESA
    # -----------------------------------------------------

    @strawberry.mutation
    def deactivate_company(
        self,
        id: strawberry.ID
    ) -> CompanyType:

        with SessionLocal() as db:

            company = db.get(
                Company,
                int(id)
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if not company.is_active:
                raise GraphQLError(
                    "La empresa ya está desactivada."
                )

            company.is_active = False

            db.commit()
            db.refresh(company)

            return company_to_type(
                company
            )


    # -----------------------------------------------------
    # CREAR ADMINISTRADOR DE EMPRESA
    # -----------------------------------------------------

    @strawberry.mutation
    def create_company_admin(
        self,
        input: CreateCompanyAdminInput
    ) -> CompanyUserType:

        with SessionLocal() as db:

            company_id = int(
                input.company_id
            )

            company = db.get(
                Company,
                company_id
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if not company.is_active:
                raise GraphQLError(
                    "La empresa está inactiva."
                )

            existing_admin = db.scalar(
                select(CompanyUser).where(
                    CompanyUser.company_id
                    == company_id,

                    CompanyUser.is_admin.is_(
                        True
                    ),

                    CompanyUser.is_active.is_(
                        True
                    ),
                )
            )

            if existing_admin:
                raise GraphQLError(
                    "La empresa ya tiene "
                    "un administrador principal."
                )

            email = normalize_email(
                input.email
            )

            existing_user = db.scalar(
                select(User).where(
                    User.email == email
                )
            )

            if existing_user:
                raise GraphQLError(
                    "El correo electrónico "
                    "ya está registrado."
                )

            try:

                password_hash = hash_password(
                    input.password
                )

            except ValueError as exc:

                raise GraphQLError(
                    str(exc)
                ) from exc

            user = User(
                name=clean_required_text(
                    input.name,
                    "El nombre"
                ),
                email=email,
                password_hash=password_hash,
            )

            db.add(user)
            db.flush()

            company_user = CompanyUser(
                company_id=company_id,
                user_id=user.id,
                is_admin=True,
            )

            db.add(company_user)

            try:

                db.commit()

            except IntegrityError as exc:

                db.rollback()

                raise GraphQLError(
                    "No se pudo crear "
                    "el administrador."
                ) from exc

            db.refresh(company_user)

            return company_user_to_type(
                company_user
            )


    # -----------------------------------------------------
    # CREAR USUARIO DE EMPRESA
    # -----------------------------------------------------

    @strawberry.mutation
    def create_company_user(
        self,
        info: strawberry.Info,
        input: CreateCompanyUserInput
    ) -> CompanyUserType:

        company_id = int(
            input.company_id
        )

        # Primero validamos que la empresa exista.
        with SessionLocal() as db:

            company = db.get(
                Company,
                company_id
            )

            if company is None:
                raise GraphQLError(
                    "La empresa no existe."
                )

            if not company.is_active:
                raise GraphQLError(
                    "La empresa está inactiva."
                )

        # Después comprobamos que quien realiza
        # la operación sea su administrador.
        ensure_company_admin(
            info,
            company_id
        )

        with SessionLocal() as db:

            email = normalize_email(
                input.email
            )

            existing_user = db.scalar(
                select(User).where(
                    User.email == email
                )
            )

            if existing_user:
                raise GraphQLError(
                    "El correo electrónico "
                    "ya está registrado."
                )

            try:

                password_hash = hash_password(
                    input.password
                )

            except ValueError as exc:

                raise GraphQLError(
                    str(exc)
                ) from exc

            user = User(
                name=clean_required_text(
                    input.name,
                    "El nombre"
                ),
                email=email,
                password_hash=password_hash,
            )

            db.add(user)
            db.flush()

            company_user = CompanyUser(
                company_id=company_id,
                user_id=user.id,
                is_admin=False,
            )

            db.add(company_user)

            try:

                db.commit()

            except IntegrityError as exc:

                db.rollback()

                raise GraphQLError(
                    "No se pudo registrar "
                    "el usuario."
                ) from exc

            db.refresh(company_user)

            return company_user_to_type(
                company_user
            )


    # -----------------------------------------------------
    # DESACTIVAR USUARIO DE EMPRESA
    # -----------------------------------------------------

    @strawberry.mutation
    def deactivate_company_user(
        self,
        info: strawberry.Info,
        id: strawberry.ID
    ) -> CompanyUserType:

        with SessionLocal() as db:

            company_user = db.get(
                CompanyUser,
                int(id)
            )

            if company_user is None:
                raise GraphQLError(
                    "La relación empresa-usuario "
                    "no existe."
                )

            company_id = (
                company_user.company_id
            )

        ensure_company_admin(
            info,
            company_id
        )

        with SessionLocal() as db:

            company_user = db.get(
                CompanyUser,
                int(id)
            )

            if company_user is None:
                raise GraphQLError(
                    "La relación empresa-usuario "
                    "no existe."
                )

            if company_user.is_admin:
                raise GraphQLError(
                    "No se puede desactivar "
                    "al administrador principal "
                    "desde esta operación."
                )

            if not company_user.is_active:
                raise GraphQLError(
                    "El usuario ya está "
                    "desactivado para esta empresa."
                )

            company_user.is_active = False

            db.commit()
            db.refresh(company_user)

            return company_user_to_type(
                company_user
            )


    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    @strawberry.mutation
    def login(
        self,
        input: LoginInput
    ) -> AuthPayload:

        email = normalize_email(
            input.email
        )

        with SessionLocal() as db:

            user = db.scalar(
                select(User).where(
                    User.email == email
                )
            )

            if (
                user is None
                or not user.is_active
                or not verify_password(
                    input.password,
                    user.password_hash
                )
            ):
                raise GraphQLError(
                    "Correo electrónico o "
                    "contraseña incorrectos."
                )

            token = create_access_token(
                user.id
            )

            return AuthPayload(
                token=token,
                token_type="Bearer",

                user=AuthUser(
                    id=strawberry.ID(
                        str(user.id)
                    ),
                    name=user.name,
                    email=user.email,
                ),
            )


# =========================================================
# SCHEMA
# =========================================================

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,

    config=StrawberryConfig(
        scalar_map={
            datetime: strawberry.scalar(
                name="Time",

                description=(
                    "Fecha y hora "
                    "en formato ISO-8601"
                ),

                serialize=lambda value: (
                    value.isoformat()
                ),

                parse_value=lambda value: (
                    datetime.fromisoformat(
                        value
                    )
                ),
            )
        }
    ),
)
