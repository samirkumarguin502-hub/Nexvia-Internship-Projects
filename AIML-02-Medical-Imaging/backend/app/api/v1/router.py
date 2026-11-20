from fastapi import APIRouter
from app.api.v1.endpoints import health,studies,inference,monitoring,auth,admin
api_router=APIRouter()
api_router.include_router(health.router,tags=['health'])
api_router.include_router(studies.router,prefix='/studies',tags=['studies'])
api_router.include_router(inference.router,prefix='/inference',tags=['inference'])
api_router.include_router(monitoring.router,prefix='/monitoring',tags=['monitoring'])

api_router.include_router(auth.router,prefix='/auth',tags=['authentication'])
api_router.include_router(admin.router,prefix='/admin',tags=['admin'],dependencies=[])
