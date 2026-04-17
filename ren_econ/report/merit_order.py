from __future__ import annotations

"""
Merit order by flat breakeven PPA (€/MWh): cheapest contract first.

Uses the same breakeven definition as `ren_econ.models.ppa` (NPV=0 flat strike on the first
10 operating years). Projects flagged `no_ppa_needed` sort as 0 €/MWh.
"""

import plotly.graph_objects as go
from jinja2 import Environment, PackageLoader, select_autoescape

from ren_econ.report.hub import HubProjectSummary


def sort_merit_order(summaries: list[HubProjectSummary]) -> list[HubProjectSummary]:
    return sorted(
        summaries,
        key=lambda r: (r.breakeven_ppa_eur_mwh if not r.no_ppa_needed else 0.0, r.asset_id),
    )


def merit_order_bar_chart_html(summaries: list[HubProjectSummary]) -> str:
    """Plotly bar chart: projects on x-axis in merit order (cheapest left), y = breakeven €/MWh."""
    ordered = sort_merit_order(summaries)
    labels = [r.asset_id for r in ordered]
    values = [r.breakeven_ppa_eur_mwh if not r.no_ppa_needed else 0.0 for r in ordered]
    hovers = [
        (
            f"<b>{r.name}</b><br>"
            f"{r.asset_id} · {r.net_capacity_mw:.0f} MW<br>"
            f"Breakeven PPA: {0 if r.no_ppa_needed else r.breakeven_ppa_eur_mwh:.2f} €/MWh"
            f"{' (not needed)' if r.no_ppa_needed else ''}<br>"
            f"Merchant NPV: {r.npv_merchant_meur:.1f} M€"
        )
        for r in ordered
    ]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
            hovertext=hovers,
            hoverinfo="text",
            marker_color="#2980b9",
        )
    )
    fig.update_layout(
        title="Merit order — breakeven flat PPA (10y, €/MWh), cheapest first",
        xaxis_title="Project",
        yaxis_title="€/MWh",
        xaxis=dict(categoryorder="array", categoryarray=labels),
        margin=dict(l=48, r=24, t=56, b=120),
        height=480,
        showlegend=False,
    )
    fig.update_xaxes(tickangle=-35)
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": True})


def render_merit_order_standalone(
    summaries: list[HubProjectSummary],
    *,
    hub_index_href: str | None = None,
) -> str:
    """Full HTML page: merit-order chart + ranked table + optional link back to portfolio index."""
    env = Environment(
        loader=PackageLoader("ren_econ.report", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("merit_order_standalone.html.j2")
    ordered = sort_merit_order(summaries)
    return tpl.render(
        merit_chart_html=merit_order_bar_chart_html(summaries),
        projects_merit=ordered,
        hub_index_href=hub_index_href,
    )
