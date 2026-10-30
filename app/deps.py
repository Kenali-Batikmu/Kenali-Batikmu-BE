from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings
from .security import decode_access_token

_bearer = HTTPBearer(auto_error=False)
_WWW = {"WWW-Authenticate": "Bearer"}


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> int:
    """ID pengguna dari access token. Tanpa query database agar cepat di jaringan lambat."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan.", headers=_WWW)
    try:
        return decode_access_token(credentials.credentials, settings)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token kedaluwarsa.", headers=_WWW)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid.", headers=_WWW)
