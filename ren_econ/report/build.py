from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

import plotly.graph_objects as go
from jinja2 import Environment, PackageLoader, select_autoescape

from ren_econ.config import ModelConfig
from ren_econ.models.cashflow import DcfResult
from ren_econ.models.costs import CostInputs
from ren_econ.models.ppa import PpaBreakeven
from ren_econ.models.project import ProjectContext


def _osm_embed_map(ctx: ProjectContext) -> str:
    """Token-free map: OpenStreetMap embed (requires network when viewing)."""
    pad = 0.35
    bbox = (
        ctx.longitude - pad,
        ctx.latitude - pad,
        ctx.longitude + pad,
        ctx.latitude + pad,
    )
    q = urlencode(
        {
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "layer": "mapnik",
            "marker": f"{ctx.latitude},{ctx.longitude}",
        }
    )
    src = f"https://www.openstreetmap.org/export/embed.html?{q}"
    return (
        f'<iframe title="Project map" width="100%" height="360" frameborder="0" scrolling="no" '
        f'style="border:0;border-radius:8px" loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
        f'src="{src}"></iframe>'
        f'<p class="note"><a href="https://www.openstreetmap.org/?mlat={ctx.latitude}&mlon={ctx.longitude}#map=10/'
        f'{ctx.latitude}/{ctx.longitude}" rel="noopener" target="_blank">Open full map</a> · '
        f"WGS84 {ctx.latitude:.4f}, {ctx.longitude:.4f}</p>"
    )


def _cashflow_figure(
    dcf: DcfResult,
    ctx: ProjectContext,
    econ: ModelConfig,
    ppa: PpaBreakeven,
) -> str:
    years = [r.calendar_year for r in dcf.rows]
    capex_neg = [-r.capex_eur / 1e6 if r.phase == "construction" else 0.0 for r in dcf.rows]
    wholesale = [r.revenue_merchant_eur / 1e6 if r.phase == "operations" else 0.0 for r in dcf.rows]

    strike = ppa.breakeven_eur_per_mwh
    ppa_rev_meur: list[float] = []
    for r in dcf.rows:
        if r.phase != "operations":
            ppa_rev_meur.append(0.0)
            continue
        op_idx = r.calendar_year - ctx.cod.year
        if 0 <= op_idx < econ.ppa_term_years and r.mwh > 0:
            ppa_rev_meur.append(strike * r.mwh / 1e6)
        else:
            ppa_rev_meur.append(0.0)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Capex (construction)",
            x=years,
            y=capex_neg,
            marker_color="#c0392b",
            hovertemplate="Year %{x}<br>Capex €m %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Wholesale (day-ahead) revenue",
            x=years,
            y=wholesale,
            marker_color="#27ae60",
            hovertemplate="Year %{x}<br>Wholesale €m %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name=f"PPA contract revenue @ {strike:.1f} €/MWh (Y1–{econ.ppa_term_years})",
            x=years,
            y=ppa_rev_meur,
            marker_color="#8e44ad",
            hovertemplate="Year %{x}<br>PPA strip €m %{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        title="Annual cashflows — wholesale vs PPA strip (first 10 operating years, €m nominal)",
        xaxis_title="Calendar year",
        yaxis_title="€ millions",
        legend_orientation="h",
        margin=dict(l=40, r=20, t=60, b=40),
        height=460,
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": True})


def render_dashboard(
    ctx: ProjectContext,
    costs: CostInputs,
    econ: ModelConfig,
    dcf: DcfResult,
    ppa: PpaBreakeven,
    hub_index_href: str | None = None,
) -> str:
    env = Environment(
        loader=PackageLoader("ren_econ.report", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("dashboard.html.j2")

    total_capex = sum(costs.capex_by_year.values())
    kw = ctx.net_capacity_mw * 1000.0
    spec_capex = total_capex / kw if kw else 0.0

    first_op = next(r for r in dcf.rows if r.phase == "operations")
    implied_cf = first_op.mwh / (8760.0 * ctx.net_capacity_mw) if ctx.net_capacity_mw > 0 else 0.0
    wholesale_y1_eur_mwh = (
        first_op.revenue_merchant_eur / first_op.mwh if first_op.mwh > 0 else 0.0
    )

    params = {
        "project_name": ctx.name,
        "asset_id": ctx.project_id,
        "net_capacity_mw": ctx.net_capacity_mw,
        "cod": str(ctx.cod),
        "analysis_start": str(ctx.analysis_start),
        "construction_end": str(ctx.construction_end),
        "currency": ctx.currency,
        "bidding_zone": ctx.bidding_zone_id,
        "discount_rate_pct": econ.discount_rate * 100.0,
        "operations_years": econ.operations_years,
        "ppa_term_years": econ.ppa_term_years,
        "total_capex_meur": total_capex / 1e6,
        "spec_capex_eur_per_kw": spec_capex,
        "opex_fixed_eur_per_kw_y": costs.opex_fixed_eur_per_kw_year,
        "opex_variable_eur_per_mwh": costs.opex_variable_eur_per_mwh,
        "npv_merchant_meur": dcf.npv_merchant_eur / 1e6,
        "irr_merchant_pct": (dcf.irr_merchant * 100.0) if dcf.irr_merchant is not None else None,
        "breakeven_ppa": ppa.breakeven_eur_per_mwh,
        "no_ppa_needed": ppa.no_ppa_needed,
        "implied_cf_y1": implied_cf,
        "pv_rev_ppa_win_meur": ppa.pv_rev_merchant_ppa_window_eur / 1e6,
        "pv_mwh_ppa_win_fmt": f"{ppa.pv_mwh_ppa_window:,.0f}",
        "undisc_avg_ppa": ppa.undiscounted_avg_eur_per_mwh,
        "wholesale_y1_eur_mwh": wholesale_y1_eur_mwh,
        "hub_index_href": hub_index_href,
    }

    html = tpl.render(
        map_html=_osm_embed_map(ctx),
        cashflow_chart=_cashflow_figure(dcf, ctx, econ, ppa),
        params=params,
    )
    return html


def write_dashboard(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
