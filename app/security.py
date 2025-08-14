from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from .config import EXPORT_API_KEY

# Esquema de API Key en header para OpenAPI/Swagger
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(x_api_key: str = Security(api_key_header)):
    if x_api_key != EXPORT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key inválida"
        )
    return True
