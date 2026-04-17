from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Economic assumptions used by the DCF engine."""

    discount_rate: float = Field(0.07, description="Real annual discount rate for project NPV")
    operations_years: int = Field(25, ge=1)
    ppa_term_years: int = Field(10, ge=1)
    degradation_rate_per_year: float = Field(0.005, description="Net energy loss per operating year")


class Paths(BaseModel):
    default_db: Path = Path("data/wind_demo.sqlite")
    default_out: Path = Path("dist/dashboard.html")
