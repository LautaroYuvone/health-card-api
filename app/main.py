from fastapi import FastAPI
from app.api.v1 import auth, summaries, share, terminology
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

# En desarrollo crea las tablas automáticamente si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Inclusión de routers modulares
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(summaries.router, prefix=settings.API_V1_STR)
app.include_router(share.router, prefix=settings.API_V1_STR)
app.include_router(terminology.router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "API de Tarjeta Sanitaria en funcionamiento"}