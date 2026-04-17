from __future__ import annotations

import argparse
from pathlib import Path

from ren_econ.config import ModelConfig, Paths
from ren_econ.db.repositories import load_asset, load_merged_hourly
from ren_econ.db.seed import write_demo_sqlite
from ren_econ.models.cashflow import build_annual_cashflows
from ren_econ.models.costs import CostProvider, default_dummy_costs
from ren_econ.models.ppa import breakeven_ppa_strike
from ren_econ.report.build import render_dashboard, write_dashboard


def _cmd_seed(args: argparse.Namespace) -> None:
    write_demo_sqlite(Path(args.db))
    print(f"Wrote demo SQLite to {args.db}")


def _cmd_build(args: argparse.Namespace) -> None:
    db = Path(args.db)
    out = Path(args.out)
    asset_id = args.asset

    ctx = load_asset(db, asset_id)
    costs = (args.cost_provider if False else None)  # noqa: B018 - placeholder hook
    cost_fn: CostProvider = default_dummy_costs
    costs = cost_fn(ctx)

    hourly = load_merged_hourly(db, asset_id)
    econ = ModelConfig()
    dcf = build_annual_cashflows(ctx, costs, hourly, econ)
    ppa = breakeven_ppa_strike(ctx, dcf, econ)

    html = render_dashboard(ctx, costs, econ, dcf, ppa)
    write_dashboard(out, html)
    print(f"Wrote dashboard to {out}")


def main() -> None:
    p = argparse.ArgumentParser(prog="ren-econ")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("seed", help="Create dummy SQLite with hourly generation and prices")
    ps.add_argument("--db", type=str, default=str(Paths().default_db))
    ps.set_defaults(func=_cmd_seed)

    pb = sub.add_parser("build", help="Run DCF + PPA and write HTML dashboard")
    pb.add_argument("--db", type=str, default=str(Paths().default_db))
    pb.add_argument("--out", type=str, default=str(Paths().default_out))
    pb.add_argument("--asset", type=str, default="DE_ONSHORE_DUMMY_01")
    pb.set_defaults(func=_cmd_build)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
