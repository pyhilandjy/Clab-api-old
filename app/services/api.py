from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from app.config import settings


class ApiKey:
    API_KEY_NAME = settings.api_name
    API_KEY = settings.api_key


api_key_header = APIKeyHeader(name=ApiKey.API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == ApiKey.API_KEY:
        return api_key
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")
