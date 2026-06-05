"""User management endpoints. All admin-only except /auth/me."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdateRole

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserOut], summary="Listar utilizadores (admin)")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(User).order_by(User.id).all()


@router.post(
    "", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Criar utilizador (admin)"
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email já registado")
    user = User(
        name=payload.name,
        email=email,
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/role", response_model=UserOut, summary="Alterar perfil (admin)")
def update_role(
    user_id: int,
    payload: UserUpdateRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    if user.id == current_user.id and payload.role.value != "admin":
        raise HTTPException(status_code=400, detail="Não pode rebaixar a sua própria conta")
    user.role = payload.role.value
    db.commit()
    db.refresh(user)
    return user


@router.get("/techs", response_model=List[UserOut], summary="Listar técnicos (para atribuição)")
def list_techs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Used by the frontend assign dropdown — available to any authenticated user."""
    return (
        db.query(User)
        .filter(User.role.in_(["tech", "admin"]), User.active == True)  # noqa: E712
        .order_by(User.name)
        .all()
    )
