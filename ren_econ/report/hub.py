from __future__ import annotations

from html import escape

import folium
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel, Field


class HubProjectSummary(BaseModel):
    asset_id: str
    name: str
    latitude: float
    longitude: float
    net_capacity_mw: float
    breakeven_ppa_eur_mwh: float
    no_ppa_needed: bool
    npv_merchant_meur: float


def _folium_projects_map(rows: list[HubProjectSummary]) -> str:
    m = folium.Map(location=[51.2, 10.45], zoom_start=6, tiles="OpenStreetMap")
    for r in rows:
        dash = f"dashboard_{r.asset_id}.html"
        ppa_txt = "0 (not needed)" if r.no_ppa_needed else f"{r.breakeven_ppa_eur_mwh:.2f} €/MWh"
        body = (
            f"<b>{escape(r.name)}</b><br/>"
            f"{escape(r.asset_id)} · {r.net_capacity_mw:.0f} MW<br/>"
            f"Breakeven PPA: {escape(ppa_txt)}<br/>"
            f"Merchant NPV: {r.npv_merchant_meur:.1f} M€<br/>"
            f'<a href="{escape(dash)}">Open economics →</a>'
        )
        folium.Marker(
            [r.latitude, r.longitude],
            tooltip=escape(r.name),
            popup=folium.Popup(body, max_width=340),
        ).add_to(m)
    return m._repr_html_()


def render_hub_index(rows: list[HubProjectSummary], merit_order_chart_html: str | None = None) -> str:
    env = Environment(
        loader=PackageLoader("ren_econ.report", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("hub.html.j2")
    return tpl.render(
        map_html=_folium_projects_map(rows),
        projects=rows,
        merit_order_chart_html=merit_order_chart_html or "",
    )
