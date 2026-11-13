import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from strawberry.fastapi import GraphQLRouter

from app.database import Base, SessionLocal, engine
from app.schema import schema
from app.seed import (
    backfill_company_user_roles,
    seed_permissions,
    seed_role_permissions,
    seed_roles,
)


# Cliente del dashboard financiero (Unidad III, Actividad 1): carpeta
# `dashboard/` en la raíz del repositorio, junto a la carpeta del backend.
DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "dashboard"

CORS_ORIGINS_DESARROLLO = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5500,http://127.0.0.1:5500"
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    Base.metadata.create_all(
        bind=engine
    )

    with SessionLocal() as db:
        seed_roles(db)
        seed_permissions(db)
        seed_role_permissions(db)
        backfill_company_user_roles(db)
        db.commit()

    yield


app = FastAPI(
    title="Actividad 6 - Control de acceso según el rol",

    description=(
        "Gestión de empresas, usuarios, cuentas, conceptos "
        "y movimientos financieros mediante GraphQL"
    ),

    lifespan=lifespan,
)


# CORS solo para desarrollo: permite abrir el dashboard desde otro puerto
# (Vite, Live Server). Servido desde /dashboard/ es el mismo origen y no se usa.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origen.strip()
        for origen in os.getenv("CORS_ORIGINS", CORS_ORIGINS_DESARROLLO).split(",")
        if origen.strip()
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


graphql_app = GraphQLRouter(
    schema,
    graphql_ide="graphiql"
)


app.include_router(
    graphql_app,
    prefix="/graphql"
)


@app.get("/")
def root():
    return {
        "message": "Actividad 5 - Gestión financiera funcionando",
        "graphql": "/graphql",
        "dashboard": "/dashboard/"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# El dashboard se sirve desde el mismo origen que el API: /dashboard/
if DASHBOARD_DIR.is_dir():
    app.mount(
        "/dashboard",
        StaticFiles(directory=DASHBOARD_DIR, html=True),
        name="dashboard",
    )
