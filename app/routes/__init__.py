from fastapi import Request, APIRouter

from . import dao

api_router = APIRouter()
api_router.include_router(dao.router)
