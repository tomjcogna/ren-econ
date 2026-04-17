from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ProjectContext(BaseModel):
    """Static project metadata used in reporting and cost hooks."""

    project_id: str
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    net_capacity_mw: float = Field(..., gt=0)
    currency: str = Field("EUR", min_length=3, max_length=3)
    bidding_zone_id: str = Field("DE_LU", description="EIC-style or internal zone key for price series")
    cod: date = Field(..., description="Commercial operation date (first operating day)")
    analysis_start: date = Field(..., description="First calendar year of cashflows (construction)")
    construction_end: date = Field(..., description="Last day of construction; operations begin next day")
