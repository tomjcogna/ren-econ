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
    Capex / OPEX vary slightly by `project_id` so breakeven PPA differs across sites.
    """
    mw = ctx.net_capacity_mw
    kw = mw * 1000.0
    h = sum(ord(c) for c in ctx.project_id)
    specific_capex_eur_per_kw = 1080.0 + (h % 28) * 4.0  # ~1080–1188 €/kW
    total_capex = specific_capex_eur_per_kw * kw

    cod_year = ctx.cod.year
    start_year = ctx.analysis_start.year
    years_build = max(1, cod_year - start_year)
    per_year = total_capex / years_build
    capex_by_year = {y: per_year for y in range(start_year, cod_year)}
    opex_fixed = 34.0 + (h % 9) * 0.6
    opex_var = 2.4 + (h % 5) * 0.15
    return CostInputs(
        capex_by_year=capex_by_year,
        opex_fixed_eur_per_kw_year=float(opex_fixed),
        opex_variable_eur_per_mwh=float(opex_var),
    )


CostProvider = Callable[[ProjectContext], CostInputs]
