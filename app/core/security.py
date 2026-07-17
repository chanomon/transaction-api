import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from core.config import settings

## Client must send the key in the "X-API-Key" header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    # auto_error=False on APIKeyHeader lets us raise a clean 401 ourselves
    # instead of FastAPI's default 403 when the header is missing
    if api_key is None or not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key

