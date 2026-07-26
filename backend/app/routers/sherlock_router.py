from fastapi import APIRouter, HTTPException
from app.services.sherlock_service import sherlock_service

router = APIRouter(prefix="/sherlock", tags=["sherlock"])

@router.get("/search/{username}")
async def search_username(username: str):
    try:
        result = await sherlock_service.search_username(username)
        return result
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))