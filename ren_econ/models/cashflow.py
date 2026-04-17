from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import pandas as pd
import pyxirr
from pydantic import BaseModel

from ren_econ.config import ModelConfig
from ren_econ.models.costs import CostInputs
from ren_econ.models.project import ProjectContext


class AnnualRow(BaseModel):
    calendar_year: int
    phase: Literal["construction", "operations"]
    mwh: float = 0.0
    revenue_merchant_eur: float = 0.0
    opex_eur: float = 0.0
    capex_eur: float = 0.0
    fcf_eur: float = 0.0

    model_config = {"frozen": True}


@dataclass(frozen=True)
class DcfResult:
    years: list[int]
    rows: list[AnnualRow]
    npv_merchant_eur: float
    irr_merchant: float | None
    discount_rate: float


def _year_phase(ctx: ProjectContext, year: int) -> Literal["construction", "operations"]:
    return "construction" if year < ctx.cod.year else "operations"


def build_annual_cashflows(
    ctx: ProjectContext,
    costs: CostInputs,
    hourly: pd.DataFrame,
    econ: ModelConfig,
) -> DcfResult:
    """
    hourly columns: ts_utc (datetime64 UTC), mwh_net, price_eur_per_mwh
    """
    if hourly.empty:
        raise ValueError("hourly dataframe is empty")

    hourly = hourly.copy()
    hourly["ts_utc"] = pd.to_datetime(hourly["ts_utc"], utc=True)
    hourly["year"] = hourly["ts_utc"].dt.year

    first_year = ctx.analysis_start.year
    last_year = ctx.cod.year + econ.operations_years - 1
    years = list(range(first_year, last_year + 1))

    kw = ctx.net_capacity_mw * 1000.0

    # Aggregate hourly to operating calendar years
    op_mask = hourly["year"] >= ctx.cod.year
    op = hourly.loc[op_mask].copy()
    op["rev_hour"] = op["price_eur_per_mwh"] * op["mwh_net"]
    grouped = op.groupby("year", sort=True).agg(
        mwh_net=("mwh_net", "sum"),
        revenue_merchant_eur=("rev_hour", "sum"),
    )

    rows: list[AnnualRow] = []
    for y in years:
        phase = _year_phase(ctx, y)
        mwh = 0.0
        rev = 0.0
        if phase == "operations":
            if y not in grouped.index:
                raise ValueError(f"missing hourly coverage for operating year {y}")
            mwh_raw = float(grouped.loc[y, "mwh_net"])
            rev_raw = float(grouped.loc[y, "revenue_merchant_eur"])
            ops_index = y - ctx.cod.year
            deg = (1.0 - econ.degradation_rate_per_year) ** ops_index
            mwh = mwh_raw * deg
            rev = rev_raw * deg
            opex = costs.opex_fixed_eur_per_kw_year * kw + costs.opex_variable_eur_per_mwh * mwh
        else:
            opex = 0.0

        capex = float(costs.capex_by_year.get(y, 0.0))
        fcf = rev - opex - capex
        rows.append(
            AnnualRow(
                calendar_year=y,
                phase=phase,
                mwh=mwh,
                revenue_merchant_eur=rev,
                opex_eur=opex,
                capex_eur=capex,
                fcf_eur=fcf,
            )
        )

    # NPV (end-of-year discounting from first model year)
    npv = 0.0
    for i, row in enumerate(rows):
        df = 1.0 / (1.0 + econ.discount_rate) ** (i + 1)
        npv += row.fcf_eur * df

    irr = _project_irr(rows)

    return DcfResult(
        years=years,
        rows=rows,
        npv_merchant_eur=npv,
        irr_merchant=irr,
        discount_rate=econ.discount_rate,
    )


def _project_irr(rows: list[AnnualRow]) -> float | None:
    dates = [datetime(y, 12, 31) for y in [r.calendar_year for r in rows]]
    amounts = [r.fcf_eur for r in rows]
    try:
        return float(pyxirr.xirr(dates, amounts))
    except Exception:
        return None
