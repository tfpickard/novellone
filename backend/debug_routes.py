from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def _dump_request(request: Request) -> dict:
    return {
        "client": request.client.host if request.client else None,
        "method": request.method,
        "url": str(request.url),
        "headers": {k: v for k, v in request.headers.items()},
    }


@router.get("/current")
async def debug_current(request: Request):
    info = _dump_request(request)
    logger.info("DEBUG /current %s", info)
    return {"debug": info, "note": "This route is not part of the API."}


@router.get("/next")
async def debug_next(request: Request):
    info = _dump_request(request)
    logger.info("DEBUG /next %s", info)
    return {"debug": info, "note": "This route is not part of the API."}
