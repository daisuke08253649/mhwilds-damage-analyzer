from typing import Annotated, Optional

from fastapi import Header
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address)


def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[str]:
    """JWT を検証して user_id を返す。未ログイン時は None を返す。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload.get("sub")
    except JWTError:
        return None
