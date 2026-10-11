from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import strawberry

from graphql import GraphQLError
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from strawberry.schema.config import StrawberryConfig

from app.database import SessionLocal
from app.models import (
    Company,
    CompanyUser,
    CompanyUserRoleModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    User,
)
from app.financial_models import Account, AccountConcept, Concept, Transaction, utcnow as financial_utcnow
from app.access import validar_acceso
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


@strawberry.enum(name="AccountType")
class AccountTypeEnum(Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    CASH = "CASH"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


@strawberry.enum(name="ConceptType")
class ConceptTypeEnum(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.enum(name="TransactionType")
class TransactionTypeEnum(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.type(name="Account")
class AccountGraphQL:
    id: strawberry.ID
    company_id: strawberry.ID
    account_type: AccountTypeEnum
    name: str
    bank_name: Optional[str]
    account_number: Optional[str]
    clabe: Optional[str]
    card_last_digits: Optional[str]
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    company: CompanyType


@strawberry.type(name="Concept")
class ConceptGraphQL:
    id: strawberry.ID
    company_id: strawberry.ID
    concept_type: ConceptTypeEnum
    name: str
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    company: CompanyType


@strawberry.type(name="AccountConcept")
class AccountConceptGraphQL:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    is_active: bool
    created_at: datetime
    account: AccountGraphQL
    concept: ConceptGraphQL


@strawberry.type(name="Transaction")
class TransactionGraphQL:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    transaction_type: TransactionTypeEnum
    amount: Decimal
    transaction_date: datetime
    captured_at: datetime
    captured_by: strawberry.ID
    short_description: Optional[str]
    long_description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    account: AccountGraphQL
    concept: ConceptGraphQL
    captured_by_user: UserType


@strawberry.type(name="Role")
class RoleType:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type(name="Permission")
class PermissionType:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type(name="RolePermission")
class RolePermissionType:
    id: strawberry.ID
    role: RoleType
    permission: PermissionType
    is_active: bool


@strawberry.type(name="CompanyUserRole")
class CompanyUserRoleType:
    id: strawberry.ID
    company_user: CompanyUserType
    role: RoleType
    is_active: bool


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
    role_id: Optional[strawberry.ID] = None


@strawberry.input
class CreateRoleInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input
class CreatePermissionInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input
class AssignPermissionToRoleInput:
    role_id: strawberry.ID
    permission_id: strawberry.ID


@strawberry.input
class AssignRoleInput:
    company_user_id: strawberry.ID
    role_id: strawberry.ID


@strawberry.input
class CreateAccountInput:
    company_id: strawberry.ID
    account_type: AccountTypeEnum
    name: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    clabe: Optional[str] = None
    card_last_digits: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@strawberry.input
class CreateConceptInput:
    company_id: strawberry.ID
    concept_type: ConceptTypeEnum
    name: str
    short_description: Optional[str] = None
    long_description: Optional[str] = None


@strawberry.input
class AssignConceptToAccountInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID


@strawberry.input
class CreateTransactionInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID
    transaction_type: TransactionTypeEnum
    amount: Decimal
    transaction_date: Optional[datetime] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


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



def account_to_type(account: Account) -> AccountGraphQL:
    return AccountGraphQL(
        id=strawberry.ID(str(account.id)),
        company_id=strawberry.ID(str(account.company_id)),
        account_type=AccountTypeEnum(account.account_type),
        name=account.name,
        bank_name=account.bank_name,
        account_number=account.account_number,
        clabe=account.clabe,
        card_last_digits=account.card_last_digits,
        short_description=account.short_description,
        long_description=account.long_description,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
        company=company_to_type(account.company),
    )


def concept_to_type(concept: Concept) -> ConceptGraphQL:
    return ConceptGraphQL(
        id=strawberry.ID(str(concept.id)),
        company_id=strawberry.ID(str(concept.company_id)),
        concept_type=ConceptTypeEnum(concept.concept_type),
        name=concept.name,
        short_description=concept.short_description,
        long_description=concept.long_description,
        is_active=concept.is_active,
        created_at=concept.created_at,
        updated_at=concept.updated_at,
        company=company_to_type(concept.company),
    )


def account_concept_to_type(relation: AccountConcept) -> AccountConceptGraphQL:
    return AccountConceptGraphQL(
        id=strawberry.ID(str(relation.id)),
        account_id=strawberry.ID(str(relation.account_id)),
        concept_id=strawberry.ID(str(relation.concept_id)),
        is_active=relation.is_active,
        created_at=relation.created_at,
        account=account_to_type(relation.account),
        concept=concept_to_type(relation.concept),
    )


def transaction_to_type(transaction: Transaction) -> TransactionGraphQL:
    return TransactionGraphQL(
        id=strawberry.ID(str(transaction.id)),
        account_id=strawberry.ID(str(transaction.account_id)),
        concept_id=strawberry.ID(str(transaction.concept_id)),
        transaction_type=TransactionTypeEnum(transaction.transaction_type),
        amount=transaction.amount,
        transaction_date=transaction.transaction_date,
        captured_at=transaction.captured_at,
        captured_by=strawberry.ID(str(transaction.captured_by)),
        short_description=transaction.short_description,
        long_description=transaction.long_description,
        is_active=transaction.is_active,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        account=account_to_type(transaction.account),
        concept=concept_to_type(transaction.concept),
        captured_by_user=user_to_type(transaction.captured_by_user),
    )


def role_to_type(role: RoleModel) -> RoleType:
    return RoleType(
        id=strawberry.ID(str(role.id)),
        code=role.code,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
    )


def permission_to_type(permission: PermissionModel) -> PermissionType:
    return PermissionType(
        id=strawberry.ID(str(permission.id)),
        code=permission.code,
        name=permission.name,
        description=permission.description,
        is_active=permission.is_active,
    )


def role_permission_to_type(relation: RolePermissionModel) -> RolePermissionType:
    return RolePermissionType(
        id=strawberry.ID(str(relation.id)),
        role=role_to_type(relation.role),
        permission=permission_to_type(relation.permission),
        is_active=relation.is_active,
    )


def company_user_role_to_type(relation: CompanyUserRoleModel) -> CompanyUserRoleType:
    return CompanyUserRoleType(
        id=strawberry.ID(str(relation.id)),
        company_user=company_user_to_type(relation.company_user),
        role=role_to_type(relation.role),
        is_active=relation.is_active,
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
        actor_company_user_id: strawberry.ID,
        company_id: strawberry.ID
    ) -> list[CompanyUserType]:

        with SessionLocal() as db:
            validar_acceso(
                db,
                actor_company_user_id,
                "company.users.read",
                target_company_id=int(company_id),
            )

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


    @strawberry.field
    def accounts(
        self,
        actor_company_user_id: strawberry.ID,
        company_id: strawberry.ID,
        account_type: Optional[AccountTypeEnum] = None,
        active_only: Optional[bool] = None,
    ) -> list[AccountGraphQL]:
        with SessionLocal() as db:
            validar_acceso(
                db,
                actor_company_user_id,
                "accounts.read",
                target_company_id=int(company_id),
            )

            company = db.get(Company, int(company_id))
            if company is None:
                raise GraphQLError("La empresa no existe.")

            stmt = select(Account).where(Account.company_id == int(company_id))
            if account_type is not None:
                stmt = stmt.where(Account.account_type == account_type.value)
            if active_only is True:
                stmt = stmt.where(Account.is_active.is_(True))
            stmt = stmt.order_by(Account.id)

            return [account_to_type(item) for item in db.scalars(stmt).all()]


    @strawberry.field
    def concepts(
        self,
        actor_company_user_id: strawberry.ID,
        company_id: strawberry.ID,
        concept_type: Optional[ConceptTypeEnum] = None,
        active_only: Optional[bool] = None,
    ) -> list[ConceptGraphQL]:
        with SessionLocal() as db:
            validar_acceso(
                db,
                actor_company_user_id,
                "concepts.read",
                target_company_id=int(company_id),
            )

            company = db.get(Company, int(company_id))
            if company is None:
                raise GraphQLError("La empresa no existe.")

            stmt = select(Concept).where(Concept.company_id == int(company_id))
            if concept_type is not None:
                stmt = stmt.where(Concept.concept_type == concept_type.value)
            if active_only is True:
                stmt = stmt.where(Concept.is_active.is_(True))
            stmt = stmt.order_by(Concept.id)

            return [concept_to_type(item) for item in db.scalars(stmt).all()]


    @strawberry.field
    def account_concepts(
        self,
        actor_company_user_id: strawberry.ID,
        account_id: strawberry.ID,
    ) -> list[AccountConceptGraphQL]:
        with SessionLocal() as db:
            account = db.get(Account, int(account_id))
            if account is None:
                raise GraphQLError("La cuenta no existe.")

            validar_acceso(
                db,
                actor_company_user_id,
                "concepts.read",
                target_company_id=account.company_id,
            )

            stmt = (
                select(AccountConcept)
                .where(AccountConcept.account_id == int(account_id))
                .order_by(AccountConcept.id)
            )
            return [account_concept_to_type(item) for item in db.scalars(stmt).all()]


    @strawberry.field
    def transactions(
        self,
        actor_company_user_id: strawberry.ID,
        account_id: Optional[strawberry.ID] = None,
        transaction_type: Optional[TransactionTypeEnum] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[TransactionGraphQL]:
        real_limit = 100 if limit is None else limit
        real_offset = 0 if offset is None else offset

        if real_limit <= 0 or real_limit > 100:
            raise GraphQLError("El limit debe estar entre 1 y 100.")
        if real_offset < 0:
            raise GraphQLError("El offset no puede ser negativo.")

        with SessionLocal() as db:
            actor = validar_acceso(
                db,
                actor_company_user_id,
                "transactions.read",
            )

            stmt = select(Transaction).join(Account).where(
                Transaction.is_active.is_(True),
                Account.company_id == actor.company_id,
            )
            if account_id is not None:
                account = db.get(Account, int(account_id))
                if account is None:
                    raise GraphQLError("La cuenta no existe.")
                if account.company_id != actor.company_id:
                    raise GraphQLError("La membresía actora no pertenece a la misma empresa del recurso.")
                stmt = stmt.where(Transaction.account_id == int(account_id))
            if transaction_type is not None:
                stmt = stmt.where(Transaction.transaction_type == transaction_type.value)
            stmt = stmt.order_by(Transaction.id).limit(real_limit).offset(real_offset)

            return [transaction_to_type(item) for item in db.scalars(stmt).all()]

    @strawberry.field
    def roles(
        self,
        actor_company_user_id: strawberry.ID,
        active_only: Optional[bool] = None,
    ) -> list[RoleType]:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.read")
            stmt = select(RoleModel).order_by(RoleModel.id)
            if active_only is True:
                stmt = stmt.where(RoleModel.is_active.is_(True))
            return [role_to_type(item) for item in db.scalars(stmt).all()]

    @strawberry.field
    def role(
        self,
        actor_company_user_id: strawberry.ID,
        id: strawberry.ID,
    ) -> Optional[RoleType]:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.read")
            item = db.get(RoleModel, int(id))
            if item is None:
                return None
            return role_to_type(item)

    @strawberry.field
    def permissions(
        self,
        actor_company_user_id: strawberry.ID,
        active_only: Optional[bool] = None,
    ) -> list[PermissionType]:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.read")
            stmt = select(PermissionModel).order_by(PermissionModel.id)
            if active_only is True:
                stmt = stmt.where(PermissionModel.is_active.is_(True))
            return [permission_to_type(item) for item in db.scalars(stmt).all()]

    @strawberry.field
    def role_permissions(
        self,
        actor_company_user_id: strawberry.ID,
        role_id: strawberry.ID,
    ) -> list[RolePermissionType]:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.read")
            role_item = db.get(RoleModel, int(role_id))
            if role_item is None:
                raise GraphQLError("El rol no existe.")

            stmt = (
                select(RolePermissionModel)
                .where(
                    RolePermissionModel.role_id == int(role_id),
                    RolePermissionModel.is_active.is_(True),
                )
                .order_by(RolePermissionModel.id)
            )
            return [role_permission_to_type(item) for item in db.scalars(stmt).all()]



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
            db.flush()

            admin_role = db.scalar(
                select(RoleModel).where(RoleModel.code == "ADMINISTRADOR")
            )

            if not admin_role:
                raise GraphQLError(
                    "El rol ADMINISTRADOR no existe en el sistema."
                )

            company_user_role = CompanyUserRoleModel(
                company_user_id=company_user.id,
                role_id=admin_role.id,
                is_active=True,
            )

            db.add(company_user_role)

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
        actor_company_user_id: strawberry.ID,
        input: CreateCompanyUserInput
    ) -> CompanyUserType:

        company_id = int(
            input.company_id
        )

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

            validar_acceso(
                db,
                actor_company_user_id,
                "company.users.write",
                target_company_id=company_id,
            )

            if input.role_id is not None:
                assigned_role = db.get(
                    RoleModel,
                    int(input.role_id)
                )

                if assigned_role is None:
                    raise GraphQLError(
                        "El rol especificado no existe."
                    )

                if not assigned_role.is_active:
                    raise GraphQLError(
                        "El rol especificado está inactivo."
                    )
            else:
                assigned_role = db.scalar(
                    select(RoleModel).where(
                        RoleModel.code == "CONSULTA"
                    )
                )

                if not assigned_role:
                    raise GraphQLError(
                        "El rol CONSULTA no existe en el sistema."
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
                is_admin=False,
            )

            db.add(company_user)
            db.flush()

            company_user_role = CompanyUserRoleModel(
                company_user_id=company_user.id,
                role_id=assigned_role.id,
                is_active=True,
            )

            db.add(company_user_role)

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
        actor_company_user_id: strawberry.ID,
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

            validar_acceso(
                db,
                actor_company_user_id,
                "company.users.write",
                target_company_id=company_user.company_id,
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
    # CUENTAS, CONCEPTOS Y RELACIONES
    # -----------------------------------------------------

    @strawberry.mutation
    def create_account(
        self,
        actor_company_user_id: strawberry.ID,
        input: CreateAccountInput,
    ) -> AccountGraphQL:
        with SessionLocal() as db:
            company_id = int(input.company_id)
            company = db.get(Company, company_id)
            if company is None:
                raise GraphQLError("La empresa no existe.")
            if not company.is_active:
                raise GraphQLError("La empresa está inactiva.")

            validar_acceso(
                db,
                actor_company_user_id,
                "accounts.write",
                target_company_id=company_id,
            )

            name = clean_required_text(input.name, "El nombre de la cuenta")
            existing = db.scalar(
                select(Account).where(
                    Account.company_id == company_id,
                    Account.name == name,
                )
            )
            if existing:
                raise GraphQLError("Ya existe una cuenta con ese nombre en la empresa.")

            account = Account(
                company_id=company_id,
                account_type=input.account_type.value,
                name=name,
                bank_name=input.bank_name.strip() if input.bank_name and input.bank_name.strip() else None,
                account_number=input.account_number.strip() if input.account_number and input.account_number.strip() else None,
                clabe=input.clabe.strip() if input.clabe and input.clabe.strip() else None,
                card_last_digits=input.card_last_digits.strip() if input.card_last_digits and input.card_last_digits.strip() else None,
                short_description=input.short_description.strip() if input.short_description and input.short_description.strip() else None,
                long_description=input.long_description.strip() if input.long_description and input.long_description.strip() else None,
            )
            db.add(account)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo crear la cuenta porque el registro está duplicado.") from exc
            db.refresh(account)
            return account_to_type(account)


    @strawberry.mutation
    def create_concept(
        self,
        actor_company_user_id: strawberry.ID,
        input: CreateConceptInput,
    ) -> ConceptGraphQL:
        with SessionLocal() as db:
            company_id = int(input.company_id)
            company = db.get(Company, company_id)
            if company is None:
                raise GraphQLError("La empresa no existe.")
            if not company.is_active:
                raise GraphQLError("La empresa está inactiva.")

            validar_acceso(
                db,
                actor_company_user_id,
                "concepts.write",
                target_company_id=company_id,
            )

            name = clean_required_text(input.name, "El nombre del concepto")
            existing = db.scalar(
                select(Concept).where(
                    Concept.company_id == company_id,
                    Concept.concept_type == input.concept_type.value,
                    Concept.name == name,
                )
            )
            if existing:
                raise GraphQLError("Ya existe ese concepto del mismo tipo en la empresa.")

            concept = Concept(
                company_id=company_id,
                concept_type=input.concept_type.value,
                name=name,
                short_description=input.short_description.strip() if input.short_description and input.short_description.strip() else None,
                long_description=input.long_description.strip() if input.long_description and input.long_description.strip() else None,
            )
            db.add(concept)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo crear el concepto porque el registro está duplicado.") from exc
            db.refresh(concept)
            return concept_to_type(concept)


    @strawberry.mutation
    def assign_concept_to_account(
        self,
        actor_company_user_id: strawberry.ID,
        input: AssignConceptToAccountInput,
    ) -> AccountConceptGraphQL:
        with SessionLocal() as db:
            account = db.get(Account, int(input.account_id))
            concept = db.get(Concept, int(input.concept_id))

            if account is None:
                raise GraphQLError("La cuenta no existe.")
            if concept is None:
                raise GraphQLError("El concepto no existe.")
            if not account.is_active:
                raise GraphQLError("La cuenta está inactiva.")
            if not concept.is_active:
                raise GraphQLError("El concepto está inactivo.")
            if account.company_id != concept.company_id:
                raise GraphQLError("La cuenta y el concepto deben pertenecer a la misma empresa.")

            validar_acceso(
                db,
                actor_company_user_id,
                "concepts.write",
                target_company_id=account.company_id,
            )

            existing = db.scalar(
                select(AccountConcept).where(
                    AccountConcept.account_id == account.id,
                    AccountConcept.concept_id == concept.id,
                )
            )
            if existing:
                if existing.is_active:
                    raise GraphQLError("El concepto ya está asignado a la cuenta.")
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                return account_concept_to_type(existing)

            relation = AccountConcept(account_id=account.id, concept_id=concept.id)
            db.add(relation)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("La relación cuenta-concepto ya existe.") from exc
            db.refresh(relation)
            return account_concept_to_type(relation)


    @strawberry.mutation
    def remove_concept_from_account(
        self,
        actor_company_user_id: strawberry.ID,
        account_id: strawberry.ID,
        concept_id: strawberry.ID,
    ) -> bool:
        with SessionLocal() as db:
            account = db.get(Account, int(account_id))
            if account is None:
                raise GraphQLError("La cuenta no existe.")

            validar_acceso(
                db,
                actor_company_user_id,
                "concepts.write",
                target_company_id=account.company_id,
            )

            relation = db.scalar(
                select(AccountConcept).where(
                    AccountConcept.account_id == int(account_id),
                    AccountConcept.concept_id == int(concept_id),
                )
            )
            if relation is None:
                raise GraphQLError("La relación cuenta-concepto no existe.")
            if not relation.is_active:
                raise GraphQLError("La relación cuenta-concepto ya está desactivada.")

            relation.is_active = False
            db.commit()
            return True


    # -----------------------------------------------------
    # MOVIMIENTOS FINANCIEROS
    # -----------------------------------------------------

    @strawberry.mutation
    def create_transaction(
        self,
        actor_company_user_id: strawberry.ID,
        input: CreateTransactionInput,
    ) -> TransactionGraphQL:
        with SessionLocal() as db:
            account = db.get(Account, int(input.account_id))
            if account is None:
                raise GraphQLError("La cuenta no existe.")
            if not account.is_active:
                raise GraphQLError("La cuenta está inactiva.")

            actor = validar_acceso(
                db,
                actor_company_user_id,
                "transactions.write",
                target_company_id=account.company_id,
            )

            concept = db.get(Concept, int(input.concept_id))
            if concept is None:
                raise GraphQLError("El concepto no existe.")
            if not concept.is_active:
                raise GraphQLError("El concepto está inactivo.")

            if account.company_id != concept.company_id:
                raise GraphQLError("La cuenta y el concepto deben pertenecer a la misma empresa.")

            allowed = db.scalar(
                select(AccountConcept).where(
                    AccountConcept.account_id == account.id,
                    AccountConcept.concept_id == concept.id,
                    AccountConcept.is_active.is_(True),
                )
            )
            if allowed is None:
                raise GraphQLError("El concepto no está permitido para la cuenta seleccionada.")

            if input.transaction_type.value != concept.concept_type:
                raise GraphQLError("El tipo de movimiento no es compatible con el tipo de concepto.")

            amount = Decimal(input.amount)
            if amount <= 0:
                raise GraphQLError("El monto del movimiento debe ser mayor que cero.")

            now = financial_utcnow()
            transaction = Transaction(
                account_id=account.id,
                concept_id=concept.id,
                transaction_type=input.transaction_type.value,
                amount=amount,
                transaction_date=input.transaction_date or now,
                captured_at=now,
                captured_by=actor.user_id,
                short_description=input.short_description.strip() if input.short_description and input.short_description.strip() else None,
                long_description=input.long_description.strip() if input.long_description and input.long_description.strip() else None,
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            return transaction_to_type(transaction)


    @strawberry.mutation
    def delete_transaction(
        self,
        actor_company_user_id: strawberry.ID,
        id: strawberry.ID,
    ) -> TransactionGraphQL:
        with SessionLocal() as db:
            transaction = db.get(Transaction, int(id))
            if transaction is None:
                raise GraphQLError("El movimiento no existe.")

            validar_acceso(
                db,
                actor_company_user_id,
                "transactions.write",
                target_company_id=transaction.account.company_id,
            )

            if not transaction.is_active:
                raise GraphQLError("El movimiento ya está eliminado.")

            transaction.is_active = False
            db.commit()
            db.refresh(transaction)
            return transaction_to_type(transaction)


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

    # -----------------------------------------------------
    # ROLES Y PERMISOS
    # -----------------------------------------------------

    @strawberry.mutation
    def create_role(
        self,
        actor_company_user_id: strawberry.ID,
        input: CreateRoleInput,
    ) -> RoleType:
        code = clean_required_text(input.code, "El código del rol").upper()
        name = clean_required_text(input.name, "El nombre del rol")
        description = (
            input.description.strip()
            if input.description and input.description.strip()
            else None
        )

        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.write")

            existing = db.scalar(
                select(RoleModel).where(RoleModel.code == code)
            )
            if existing:
                raise GraphQLError("El código de rol ya está registrado.")

            role = RoleModel(
                code=code,
                name=name,
                description=description,
                is_active=True,
            )
            db.add(role)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("El código de rol ya está registrado.") from exc

            db.refresh(role)
            return role_to_type(role)

    @strawberry.mutation
    def deactivate_role(
        self,
        actor_company_user_id: strawberry.ID,
        id: strawberry.ID,
    ) -> RoleType:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.write")

            role = db.get(RoleModel, int(id))
            if role is None:
                raise GraphQLError("El rol no existe.")

            if not role.is_active:
                raise GraphQLError("El rol ya está desactivado.")

            role.is_active = False
            db.commit()
            db.refresh(role)
            return role_to_type(role)

    @strawberry.mutation
    def create_permission(
        self,
        actor_company_user_id: strawberry.ID,
        input: CreatePermissionInput,
    ) -> PermissionType:
        code = clean_required_text(input.code, "El código del permiso").lower()
        name = clean_required_text(input.name, "El nombre del permiso")
        description = (
            input.description.strip()
            if input.description and input.description.strip()
            else None
        )

        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.write")

            existing = db.scalar(
                select(PermissionModel).where(PermissionModel.code == code)
            )
            if existing:
                raise GraphQLError("El código de permiso ya está registrado.")

            perm = PermissionModel(
                code=code,
                name=name,
                description=description,
                is_active=True,
            )
            db.add(perm)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError(
                    "El código de permiso ya está registrado."
                ) from exc

            db.refresh(perm)
            return permission_to_type(perm)

    @strawberry.mutation
    def assign_permission_to_role(
        self,
        actor_company_user_id: strawberry.ID,
        input: AssignPermissionToRoleInput,
    ) -> RolePermissionType:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.write")

            role_id = int(input.role_id)
            permission_id = int(input.permission_id)

            role = db.get(RoleModel, role_id)
            if role is None:
                raise GraphQLError("El rol no existe.")
            if not role.is_active:
                raise GraphQLError("El rol está inactivo.")

            permission = db.get(PermissionModel, permission_id)
            if permission is None:
                raise GraphQLError("El permiso no existe.")
            if not permission.is_active:
                raise GraphQLError("El permiso está inactivo.")

            existing_rp = db.scalar(
                select(RolePermissionModel).where(
                    RolePermissionModel.role_id == role_id,
                    RolePermissionModel.permission_id == permission_id,
                )
            )

            if existing_rp:
                if existing_rp.is_active:
                    raise GraphQLError(
                        "El permiso ya está asignado y activo para este rol."
                    )
                existing_rp.is_active = True
                db.commit()
                db.refresh(existing_rp)
                return role_permission_to_type(existing_rp)

            rp = RolePermissionModel(
                role_id=role_id,
                permission_id=permission_id,
                is_active=True,
            )
            db.add(rp)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError(
                    "No se pudo asignar el permiso al rol."
                ) from exc

            db.refresh(rp)
            return role_permission_to_type(rp)

    @strawberry.mutation
    def remove_permission_from_role(
        self,
        actor_company_user_id: strawberry.ID,
        role_id: strawberry.ID,
        permission_id: strawberry.ID,
    ) -> bool:
        with SessionLocal() as db:
            validar_acceso(db, actor_company_user_id, "roles.write")

            rp = db.scalar(
                select(RolePermissionModel).where(
                    RolePermissionModel.role_id == int(role_id),
                    RolePermissionModel.permission_id == int(permission_id),
                )
            )

            if rp is None or not rp.is_active:
                raise GraphQLError(
                    "El permiso no está asignado activamente a este rol."
                )

            rp.is_active = False
            db.commit()
            return True

    @strawberry.mutation
    def assign_role(
        self,
        actor_company_user_id: strawberry.ID,
        input: AssignRoleInput,
    ) -> CompanyUserRoleType:
        with SessionLocal() as db:
            company_user_id = int(input.company_user_id)
            role_id = int(input.role_id)

            company_user = db.get(CompanyUser, company_user_id)
            if company_user is None:
                raise GraphQLError("La membresía de usuario no existe.")
            if not company_user.is_active:
                raise GraphQLError("La membresía de usuario está inactiva.")

            validar_acceso(
                db,
                actor_company_user_id,
                "roles.write",
                target_company_id=company_user.company_id,
            )

            role = db.get(RoleModel, role_id)
            if role is None:
                raise GraphQLError("El rol no existe.")
            if not role.is_active:
                raise GraphQLError("El rol está inactivo.")

            active_roles = db.scalars(
                select(CompanyUserRoleModel).where(
                    CompanyUserRoleModel.company_user_id == company_user_id,
                    CompanyUserRoleModel.is_active.is_(True),
                )
            ).all()

            for ar in active_roles:
                if ar.role_id != role_id:
                    ar.is_active = False

            target_cur = db.scalar(
                select(CompanyUserRoleModel).where(
                    CompanyUserRoleModel.company_user_id == company_user_id,
                    CompanyUserRoleModel.role_id == role_id,
                )
            )

            if target_cur:
                target_cur.is_active = True
            else:
                target_cur = CompanyUserRoleModel(
                    company_user_id=company_user_id,
                    role_id=role_id,
                    is_active=True,
                )
                db.add(target_cur)

            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise GraphQLError("No se pudo asignar el rol a la membresía.") from exc

            db.refresh(target_cur)
            return company_user_role_to_type(target_cur)



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
