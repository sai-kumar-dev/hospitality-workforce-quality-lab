"""Top-level API router."""

from fastapi import APIRouter

from shiftbridge_api.api.routes import applications, auth, jobs

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
