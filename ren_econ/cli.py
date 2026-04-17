from __future__ import annotations

import argparse
from pathlib import Path

from ren_econ.config import ModelConfig, Paths
from ren_econ.db.repositories import list_asset_ids, load_asset, load_merged_hourly
from ren_econ.db.seed import write_demo_sqlite
from ren_econ.models.cashflow import DcfResult, build_annual_cashflows
from ren_econ.models.costs import CostInputs, CostProvider, default_dummy_costs
from ren_econ.models.ppa import PpaBreakeven, breakeven_ppa_strike
from ren_econ.models.project import ProjectContext
from ren_econ.report.build import render_dashboard, write_dashboard
from ren_econ.report.hub import HubProjectSummary, render_hub_index
from ren_econ.report.merit_order import merit_order_bar_chart_html, render_merit_order_standalone


def _run_model(db: Path, asset_id: str) -> tuple[ProjectContext, CostInputs, ModelConfig, DcfResult, PpaBreakeven]:
    ctx = load_asset(db, asset_id)
    cost_fn: CostProvider = default_dummy_costs
    costs = cost_fn(ctx)
    hourly = load_merged_hourly(db, asset_id)
    econ = ModelConfig()
    dcf = build_annual_cashflows(ctx, costs, hourly, econ)
    ppa = breakeven_ppa_strike(ctx, dcf, econ)
    return ctx, costs, econ, dcf, ppa


def _cmd_seed(args: argparse.Namespace) -> None:
    write_demo_sqlite(Path(args.db))
    print(f"Wrote demo SQLite to {args.db}")


def _cmd_build(args: argparse.Namespace) -> None:
    db = Path(args.db)
    out = Path(args.out)
    hub = (args.hub_index or "").strip() or None
    ctx, costs, econ, dcf, ppa = _run_model(db, args.asset)
    html = render_dashboard(ctx, costs, econ, dcf, ppa, hub_index_href=hub)
    write_dashboard(out, html)
    print(f"Wrote dashboard to {out}")


def _cmd_merit_order(args: argparse.Namespace) -> None:
    db = Path(args.db)
    out = Path(args.out)
    hub = (args.hub_index or "").strip() or None
    summaries: list[HubProjectSummary] = []
    for asset_id in list_asset_ids(db):
        ctx, costs, econ, dcf, ppa = _run_model(db, asset_id)
        summaries.append(
            HubProjectSummary(
                asset_id=ctx.project_id,
                name=ctx.name,
                latitude=ctx.latitude,
                longitude=ctx.longitude,
                net_capacity_mw=ctx.net_capacity_mw,
                breakeven_ppa_eur_mwh=ppa.breakeven_eur_per_mwh,
                no_ppa_needed=ppa.no_ppa_needed,
                npv_merchant_meur=dcf.npv_merchant_eur / 1e6,
            )
        )
    html = render_merit_order_standalone(summaries, hub_index_href=hub)
    write_dashboard(out, html)
    print(f"Wrote merit order report to {out}")


def _cmd_build_index(args: argparse.Namespace) -> None:
    db = Path(args.db)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[HubProjectSummary] = []
    for asset_id in list_asset_ids(db):
        ctx, costs, econ, dcf, ppa = _run_model(db, asset_id)
        dash_path = out_dir / f"dashboard_{asset_id}.html"
        html = render_dashboard(ctx, costs, econ, dcf, ppa, hub_index_href="index.html")
        write_dashboard(dash_path, html)
        summaries.append(
            HubProjectSummary(
                asset_id=ctx.project_id,
                name=ctx.name,
                latitude=ctx.latitude,
                longitude=ctx.longitude,
                net_capacity_mw=ctx.net_capacity_mw,
                breakeven_ppa_eur_mwh=ppa.breakeven_eur_per_mwh,
                no_ppa_needed=ppa.no_ppa_needed,
                npv_merchant_meur=dcf.npv_merchant_eur / 1e6,
            )
        )
    merit_html = merit_order_bar_chart_html(summaries)
    idx_html = render_hub_index(summaries, merit_order_chart_html=merit_html)
    write_dashboard(out_dir / "index.html", idx_html)
    merit_page = render_merit_order_standalone(summaries, hub_index_href="index.html")
    write_dashboard(out_dir / "merit_order.html", merit_page)
    print(f"Wrote {len(summaries)} dashboards + index.html + merit_order.html under {out_dir}")


def main() -> None:
    p = argparse.ArgumentParser(prog="ren-econ")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("seed", help="Create dummy SQLite with 10 projects and hourly series")
    ps.add_argument("--db", type=str, default=str(Paths().default_db))
    ps.set_defaults(func=_cmd_seed)

    pb = sub.add_parser("build", help="Run DCF + PPA and write one HTML dashboard")
    pb.add_argument("--db", type=str, default=str(Paths().default_db))
    pb.add_argument("--out", type=str, default=str(Paths().default_out))
    pb.add_argument("--asset", type=str, default="DE_WIND_01")
    pb.add_argument(
        "--hub-index",
        type=str,
        default="",
        metavar="HREF",
        help='Optional link back to portfolio (e.g. "index.html")',
    )
    pb.set_defaults(func=_cmd_build)

    pi = sub.add_parser(
        "build-index",
        help="Build portfolio index.html (map + table) and one dashboard per asset",
    )
    pi.add_argument("--db", type=str, default=str(Paths().default_db))
    pi.add_argument("--out-dir", type=str, default="dist")
    pi.set_defaults(func=_cmd_build_index)

    pm = sub.add_parser(
        "merit-order",
        help="Build standalone merit_order.html (bar chart + table) from the database",
    )
    pm.add_argument("--db", type=str, default=str(Paths().default_db))
    pm.add_argument("--out", type=str, default="dist/merit_order.html")
    pm.add_argument(
        "--hub-index",
        type=str,
        default="",
        metavar="HREF",
        help='Optional link to portfolio index (e.g. "index.html") when file lives in dist/',
    )
    pm.set_defaults(func=_cmd_merit_order)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
