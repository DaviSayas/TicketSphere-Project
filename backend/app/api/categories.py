"""Category endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.common import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[CategoryOut], summary="Listar categorias")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Category).order_by(Category.name).all()


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar categoria (admin)",
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Categoria já existe")
    cat = Category(
        name=payload.name,
        default_sla_hours=payload.default_sla_hours,
        auto_assign_to_user_id=payload.auto_assign_to_user_id,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat
