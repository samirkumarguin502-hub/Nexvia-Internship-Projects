from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import bootstrap_admin


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    bootstrap_admin()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version='0.3.0',
    description='Educational/research API; not for clinical use.',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get('/health', tags=['health'])
def health():
    return {'status': 'ok', 'service': 'aiml-02-api', 'environment': settings.ENVIRONMENT}
