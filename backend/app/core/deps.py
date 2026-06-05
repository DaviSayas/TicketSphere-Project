"""Reusable FastAPI dependencies: current user, role guards."""
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the JWT and load the user. Raises 401 on any failure."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exc

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.active:
        raise credentials_exc
    return user


def require_roles(*allowed: UserRole):
    """Build a dependency that allows only specific roles."""
    allowed_values = {r.value for r in allowed}

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissões para esta operação",
            )
        return user

    return _checker


# Common shortcuts
require_admin = require_roles(UserRole.ADMIN)
require_tech_or_admin = require_roles(UserRole.ADMIN, UserRole.TECH)
