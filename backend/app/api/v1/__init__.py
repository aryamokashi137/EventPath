from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.activities import router as activities_router

api_router = APIRouter()
api_router.include_router(projects_router)
api_router.include_router(activities_router)
