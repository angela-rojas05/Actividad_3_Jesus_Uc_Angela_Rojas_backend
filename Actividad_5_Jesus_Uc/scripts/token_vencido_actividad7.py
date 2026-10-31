"""Imprime un token de Ana ya VENCIDO (para el caso B11).

Firma con el mismo JWT_SECRET del .env, pero con `exp` un minuto en el pasado,
así que el servidor debe rechazarlo.  Lee los IDs de scripts/ids_demo_a7.json.

Uso:  python scripts/token_vencido_actividad7.py
"""
import json
import sys
import time
from pathlib import Path

import jwt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.security import ALGORITHM, JWT_SECRET  # noqa: E402

ana = json.loads((ROOT / "scripts" / "ids_demo_a7.json").read_text("utf-8"))["personas"]["ana"]
print(jwt.encode(
    {"companyUserId": ana["companyUserId"], "companyId": ana["companyId"],
     "exp": int(time.time()) - 60},
    JWT_SECRET, algorithm=ALGORITHM))
