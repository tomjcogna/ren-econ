from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from ren_econ.models.project import ProjectContext


def list_asset_ids(db_path: Path) -> list[str]:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    q = text("SELECT asset_id FROM assets ORDER BY asset_id")
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(q)]


def load_asset(db_path: Path, asset_id: str) -> ProjectContext:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    q = text(
        """
        SELECT asset_id, name, latitude, longitude, net_capacity_mw, currency,
               bidding_zone_id, cod_date, analysis_start_date, construction_end_date
        FROM assets
        WHERE asset_id = :aid
        """
    )
    with engine.connect() as conn:
        row = conn.execute(q, {"aid": asset_id}).mappings().one()
    return ProjectContext(
        project_id=row["asset_id"],
        name=row["name"],
        latitude=float(row["latitude"]),
        longitude=float(row["longitude"]),
        net_capacity_mw=float(row["net_capacity_mw"]),
        currency=row["currency"],
        bidding_zone_id=row["bidding_zone_id"],
        cod=date.fromisoformat(row["cod_date"]),
        analysis_start=date.fromisoformat(row["analysis_start_date"]),
        construction_end=date.fromisoformat(row["construction_end_date"]),
    )


def load_merged_hourly(db_path: Path, asset_id: str) -> pd.DataFrame:
    """
    Hourly table for one asset: merged generation with **that asset's** wholesale curve.

    columns: ts_utc (datetime64[ns, UTC]), mwh_net, price_eur_per_mwh
    """
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    q = text(
        """
        SELECT g.ts_utc AS ts_utc,
               g.mwh_net AS mwh_net,
               p.price_eur_per_mwh AS price_eur_per_mwh
        FROM generation_hourly g
        JOIN day_ahead_prices_hourly p
          ON p.asset_id = g.asset_id AND p.ts_utc = g.ts_utc
        WHERE g.asset_id = :aid
        ORDER BY g.ts_utc
        """
    )
    df = pd.read_sql_query(q, engine, params={"aid": asset_id})
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df
