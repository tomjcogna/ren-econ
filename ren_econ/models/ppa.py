from __future__ import annotations

from dataclasses import dataclass

from ren_econ.config import ModelConfig
from ren_econ.models.cashflow import AnnualRow, DcfResult
from ren_econ.models.project import ProjectContext


@dataclass(frozen=True)
class PpaBreakeven:
    breakeven_eur_per_mwh: float
    pv_rev_merchant_ppa_window_eur: float
    pv_mwh_ppa_window: float
    npv_merchant_eur: float
    undiscounted_avg_eur_per_mwh: float | None
    no_ppa_needed: bool


def breakeven_ppa_strike(
    ctx: ProjectContext,
    dcf: DcfResult,
    econ: ModelConfig,
) -> PpaBreakeven:
    """
    Flat real EUR/MWh on all MWh in the first `econ.ppa_term_years` operating years such that,
    if merchant revenue in that window were replaced by p * MWh (merchant elsewhere unchanged),
    project NPV would be zero.

    Closed form: p = (PV_rev_window - NPV_merchant) / PV_Q_window
    """
    op_rows = [r for r in dcf.rows if r.phase == "operations"]
    if len(op_rows) < econ.ppa_term_years:
        raise ValueError("not enough operating years for PPA window")

    window = op_rows[: econ.ppa_term_years]

    def df_for_row(row: AnnualRow) -> float:
        idx = next(i for i, r in enumerate(dcf.rows) if r.calendar_year == row.calendar_year)
        return 1.0 / (1.0 + econ.discount_rate) ** (idx + 1)

    pv_rev = sum(r.revenue_merchant_eur * df_for_row(r) for r in window)
    pv_q = sum(r.mwh * df_for_row(r) for r in window)
    sum_mwh = sum(r.mwh for r in window)

    npv_m = dcf.npv_merchant_eur
    if pv_q <= 0:
        raise ValueError("PV of MWh in PPA window is non-positive")

    numerator = pv_rev - npv_m
    no_ppa = numerator <= 0
    p = 0.0 if no_ppa else numerator / pv_q
    undisc = (numerator / sum_mwh) if sum_mwh > 0 else None

    return PpaBreakeven(
        breakeven_eur_per_mwh=float(p),
        pv_rev_merchant_ppa_window_eur=float(pv_rev),
        pv_mwh_ppa_window=float(pv_q),
        npv_merchant_eur=float(npv_m),
        undiscounted_avg_eur_per_mwh=float(undisc) if undisc is not None else None,
        no_ppa_needed=bool(no_ppa),
    )
