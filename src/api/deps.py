import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.session import get_session

api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


async def check_api_key(api_key: Annotated[str | None, Depends(api_key_header)]) -> None:
    if api_key is None or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid or missing API key')


SessionDep = Annotated[AsyncSession, Depends(get_session)]
