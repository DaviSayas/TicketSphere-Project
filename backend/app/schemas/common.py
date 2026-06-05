"""Schemas for categories and dashboard."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    default_sla_hours: int
    auto_assign_to_user_id: Optional[int] = None


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    default_sla_hours: int = Field(default=24, ge=1, le=720)
    auto_assign_to_user_id: Optional[int] = None


# ---------- Dashboard ----------

class DashboardCard(BaseModel):
    open_tickets: int
    resolved_last_30d: int
    sla_breached_last_30d: int
    avg_resolution_hours: float


class DailySeriesPoint(BaseModel):
    date: str  # YYYY-MM-DD
    created: int
    resolved: int


class TopTech(BaseModel):
    user_id: int
    name: str
    resolved: int
    avg_resolution_hours: float
    sla_compliance_pct: float


class CategoryDistribution(BaseModel):
    category: str
    count: int


class DashboardResponse(BaseModel):
    cards: DashboardCard
    daily_series: List[DailySeriesPoint]
    top_techs: List[TopTech]
    category_distribution: List[CategoryDistribution]
