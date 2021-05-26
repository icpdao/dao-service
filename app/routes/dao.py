import os

from fastapi import Request, APIRouter

router = APIRouter()


@router.get('/test')
async def test(request: Request):
    return {
        "success": True
    }
