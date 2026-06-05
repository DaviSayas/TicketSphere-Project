"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_response(user: User) -> TokenResponse:
    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse, summary="Login com email/password")
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    """JSON login endpoint — preferred by the SPA frontend."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    return _build_token_response(user)


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2-form-encoded variant — used by Swagger UI's Authorize button."""
    user = db.query(User).filter(User.email == form.username.lower()).first()
    if not user or not user.active or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _build_token_response(user)


@router.get("/me", response_model=UserOut, summary="Perfil do utilizador autenticado")
def me(current_user: User = Depends(get_current_user)):
    return current_user
