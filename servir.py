"""Levanta la API de la demo en tu compu.

    pip install -r requirements.txt
    python servir.py          ->  http://127.0.0.1:8000/docs
"""
import uvicorn
from fastapi import FastAPI

from comparador.api import router

app = FastAPI(title="Comparador de costos · demo",
              description="El motor de cruce corriendo sobre el set de datos ficticios.")
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
