import pytest
from app.database import SessionLocal
from app.access import exigir_permiso
from app.models import (
    Company,
    CompanyUser,
    CompanyUserRoleModel,
    RoleModel,
    User,
)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def setup_test_users(db_session):
    company = Company(name="Test Permisos Co", is_active=True)
    db_session.add(company)
    db_session.flush()

    # Roles preexistentes del seed
    contador_role = db_session.query(RoleModel).filter(RoleModel.code == "CONTADOR").first()
    capturista_role = db_session.query(RoleModel).filter(RoleModel.code == "CAPTURISTA").first()
    consulta_role = db_session.query(RoleModel).filter(RoleModel.code == "CONSULTA").first()

    assert contador_role is not None
    assert capturista_role is not None
    assert consulta_role is not None

    # Usuario Contador
    u_contador = User(name="User Contador", email="u_contador@test.com", password_hash="dummy12345", is_active=True)
    db_session.add(u_contador)
    db_session.flush()
    cu_contador = CompanyUser(company_id=company.id, user_id=u_contador.id, is_active=True)
    db_session.add(cu_contador)
    db_session.flush()
    db_session.add(CompanyUserRoleModel(company_user_id=cu_contador.id, role_id=contador_role.id, is_active=True))

    # Usuario Capturista
    u_capturista = User(name="User Capturista", email="u_capturista@test.com", password_hash="dummy12345", is_active=True)
    db_session.add(u_capturista)
    db_session.flush()
    cu_capturista = CompanyUser(company_id=company.id, user_id=u_capturista.id, is_active=True)
    db_session.add(cu_capturista)
    db_session.flush()
    db_session.add(CompanyUserRoleModel(company_user_id=cu_capturista.id, role_id=capturista_role.id, is_active=True))

    # Usuario Consulta
    u_consulta = User(name="User Consulta", email="u_consulta@test.com", password_hash="dummy12345", is_active=True)
    db_session.add(u_consulta)
    db_session.flush()
    cu_consulta = CompanyUser(company_id=company.id, user_id=u_consulta.id, is_active=True)
    db_session.add(cu_consulta)
    db_session.flush()
    db_session.add(CompanyUserRoleModel(company_user_id=cu_consulta.id, role_id=consulta_role.id, is_active=True))

    # Usuario Sin Rol
    u_sin_rol = User(name="User Sin Rol", email="u_sin_rol@test.com", password_hash="dummy12345", is_active=True)
    db_session.add(u_sin_rol)
    db_session.flush()
    cu_sin_rol = CompanyUser(company_id=company.id, user_id=u_sin_rol.id, is_active=True)
    db_session.add(cu_sin_rol)

    db_session.commit()

    context = {
        "company_id": company.id,
        "contador_id": cu_contador.id,
        "capturista_id": cu_capturista.id,
        "consulta_id": cu_consulta.id,
        "sin_rol_id": cu_sin_rol.id,
        "user_ids": [u_contador.id, u_capturista.id, u_consulta.id, u_sin_rol.id],
        "cu_ids": [cu_contador.id, cu_capturista.id, cu_consulta.id, cu_sin_rol.id],
    }

    yield context

    # Limpieza
    db_session.query(CompanyUserRoleModel).filter(
        CompanyUserRoleModel.company_user_id.in_(context["cu_ids"])
    ).delete(synchronize_session=False)
    db_session.query(CompanyUser).filter(
        CompanyUser.id.in_(context["cu_ids"])
    ).delete(synchronize_session=False)
    db_session.query(User).filter(
        User.id.in_(context["user_ids"])
    ).delete(synchronize_session=False)
    db_session.query(Company).filter(
        Company.id == context["company_id"]
    ).delete(synchronize_session=False)
    db_session.commit()


def test_capturista_permisos_si_y_no(db_session, setup_test_users):
    capturista_id = setup_test_users["capturista_id"]

    # Capturista SÍ puede registrar transacciones
    exigir_permiso(db_session, capturista_id, "transactions.write")
    exigir_permiso(db_session, capturista_id, "transactions.read")

    # Capturista NO puede gestionar cuentas ni conceptos
    with pytest.raises(PermissionError) as exc_info:
        exigir_permiso(db_session, capturista_id, "accounts.write")
    assert "El rol no tiene el permiso accounts.write" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info_concepts:
        exigir_permiso(db_session, capturista_id, "concepts.write")
    assert "El rol no tiene el permiso concepts.write" in str(exc_info_concepts.value)


def test_consulta_permisos_no(db_session, setup_test_users):
    consulta_id = setup_test_users["consulta_id"]

    # Consulta SÍ puede leer
    exigir_permiso(db_session, consulta_id, "transactions.read")
    exigir_permiso(db_session, consulta_id, "accounts.read")

    # Consulta NO puede escribir transacciones
    with pytest.raises(PermissionError) as exc_info_tx:
        exigir_permiso(db_session, consulta_id, "transactions.write")
    assert "El rol no tiene el permiso transactions.write" in str(exc_info_tx.value)

    # Consulta NO puede crear cuentas
    with pytest.raises(PermissionError) as exc_info_acc:
        exigir_permiso(db_session, consulta_id, "accounts.write")
    assert "El rol no tiene el permiso accounts.write" in str(exc_info_acc.value)


def test_contador_permisos_si(db_session, setup_test_users):
    contador_id = setup_test_users["contador_id"]

    # Contador SÍ puede gestionar cuentas, conceptos y transacciones
    exigir_permiso(db_session, contador_id, "accounts.write")
    exigir_permiso(db_session, contador_id, "concepts.write")
    exigir_permiso(db_session, contador_id, "transactions.write")
    exigir_permiso(db_session, contador_id, "accounts.read")

    # Contador NO puede gestionar usuarios ni roles
    with pytest.raises(PermissionError) as exc_info_users:
        exigir_permiso(db_session, contador_id, "company.users.write")
    assert "El rol no tiene el permiso company.users.write" in str(exc_info_users.value)


def test_membresia_sin_rol_activo(db_session, setup_test_users):
    sin_rol_id = setup_test_users["sin_rol_id"]

    with pytest.raises(PermissionError) as exc_info:
        exigir_permiso(db_session, sin_rol_id, "transactions.read")
    assert "La membresía no tiene un rol activo" in str(exc_info.value)
