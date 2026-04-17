from __future__ import annotations

from collections.abc import Callable
from datetime import date

from pydantic import BaseModel, Field

from ren_econ.models.project import ProjectContext


class CostInputs(BaseModel):
    """Annual capex/opex in nominal model currency (here EUR)."""

    # calendar_year -> total capex cash spend (positive number); only non-zero in construction years
    capex_by_year: dict[int, float] = Field(default_factory=dict)
    opex_fixed_eur_per_kw_year: float = Field(35.0, description="Fixed O&M EUR per kW-year")
    opex_variable_eur_per_mwh: float = Field(2.5, description="Variable O&M EUR/MWh")


def default_dummy_costs(ctx: ProjectContext) -> CostInputs:
    """
    Placeholder cost function: swap for your internal estimator.

    Uses a simple 2-year construction capex spread before COD.
    """
    mw = ctx.net_capacity_mw
    kw = mw * 1000.0
    # Rough onshore DE benchmark: EUR/kW installed (toy numbers)
    specific_capex_eur_per_kw = 1180.0
    total_capex = specific_capex_eur_per_kw * kw

    cod_year = ctx.cod.year
    start_year = ctx.analysis_start.year
    years_build = max(1, cod_year - start_year)
    per_year = total_capex / years_build
    capex_by_year = {y: per_year for y in range(start_year, cod_year)}
    return CostInputs(
        capex_by_year=capex_by_year,
        opex_fixed_eur_per_kw_year=38.0,
        opex_variable_eur_per_mwh=2.8,
    )


CostProvider = Callable[[ProjectContext], CostInputs]
