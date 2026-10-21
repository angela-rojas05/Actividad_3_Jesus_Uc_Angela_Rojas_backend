import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

ALGORITHM = "HS256"
TOKEN_MINUTES = 30

JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError(
        "Falta la variable de entorno JWT_SECRET. "
        "Genérala con: python -c \"import secrets; "
        "print(secrets.token_hex(32))\" y colócala en el archivo .env"
    )

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError(
            "La contraseña debe tener al menos 8 caracteres."
        )

    return password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str
) -> bool:
    return password_hasher.verify(
        password,
        password_hash
    )


def crear_token(company_user_id: int, company_id: int) -> str:
    """JWT firmado (HS256) sin contraseña, hash ni permisos."""
    payload = {
        "companyUserId": company_user_id,
        "companyId": company_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
