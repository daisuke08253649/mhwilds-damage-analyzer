from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address)


def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[str]:
    """JWT を検証して user_id を返す。未ログイン時は None を返す。"""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    token = token.strip()
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload.get("sub")
    except JWTError:
        return None


def get_current_user_required(
    user_id: Annotated[Optional[str], Depends(get_current_user)],
) -> str:
    """認証済みユーザーの user_id を返す。未認証は 401 を返す。"""
    if not user_id:
        raise HTTPException(status_code=401, detail="認証が必要です")
    return user_id
