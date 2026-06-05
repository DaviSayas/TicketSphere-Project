"""Category ORM model."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    default_sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    # Optional default assignee for round-robin / auto-assignment
    auto_assign_to_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    tickets = relationship("Ticket", back_populates="category")
