from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text


SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    net_capacity_mw REAL NOT NULL,
    currency TEXT NOT NULL,
    bidding_zone_id TEXT NOT NULL,
    cod_date TEXT NOT NULL,
    analysis_start_date TEXT NOT NULL,
    construction_end_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_hourly (
    asset_id TEXT NOT NULL,
    ts_utc TEXT NOT NULL,
    mwh_net REAL NOT NULL,
    PRIMARY KEY (asset_id, ts_utc),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS day_ahead_prices_hourly (
    ts_utc TEXT NOT NULL,
    bidding_zone_id TEXT NOT NULL,
    price_eur_per_mwh REAL NOT NULL,
    PRIMARY KEY (ts_utc, bidding_zone_id)
);

CREATE INDEX IF NOT EXISTS idx_gen_asset_ts ON generation_hourly (asset_id, ts_utc);
CREATE INDEX IF NOT EXISTS idx_price_zone_ts ON day_ahead_prices_hourly (bidding_zone_id, ts_utc);
"""


def write_demo_sqlite(path: Path) -> None:
    """
    Create a SQLite file with a ~200 MW German onshore dummy project and 25y of hourly series.

    Timestamps are ISO8601 strings in UTC to mirror typical warehouse exports.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as conn:
        for stmt in SCHEMA_DDL.strip().split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

    asset_id = "DE_ONSHORE_DUMMY_01"
    zone = "DE_LU"
    capacity_mw = 200.0

    asset_row = {
        "asset_id": asset_id,
        "name": "Dummy North German Plain Wind Cluster",
        "latitude": 53.9242,
        "longitude": 9.1811,
        "net_capacity_mw": capacity_mw,
        "currency": "EUR",
        "bidding_zone_id": zone,
        "cod_date": "2026-01-01",
        "analysis_start_date": "2024-01-01",
        "construction_end_date": "2025-12-31",
    }
    pd.DataFrame([asset_row]).to_sql("assets", engine, if_exists="append", index=False)

    # Operating horizon: full calendar years from COD through 25 years
    start = pd.Timestamp("2026-01-01", tz="UTC")
    end = pd.Timestamp("2050-12-31 23:00", tz="UTC")
    hours = pd.date_range(start, end, freq="h", tz="UTC")
    n = len(hours)

    hour_of_year = ((hours.dayofyear - 1) * 24 + hours.hour).astype(int) % 8760
    seasonal = 0.12 * np.sin(2 * np.pi * hour_of_year / 8760.0)
    diurnal = 0.04 * np.sin(2 * np.pi * hours.hour / 24.0)
    noise_cf = np.random.default_rng(42).normal(0.0, 0.02, size=n)
    capacity_factor = np.clip(0.28 + seasonal + diurnal + noise_cf, 0.02, 0.95)
    mwh_net = capacity_factor * capacity_mw

    base_price = 78.0
    seasonal_p = 18.0 * np.sin(2 * np.pi * hour_of_year / 8760.0 + 0.7)
    noise_p = np.random.default_rng(43).normal(0.0, 9.0, size=n)
    price = np.clip(base_price + seasonal_p + noise_p, -200.0, 400.0)

    ts_iso = hours.strftime("%Y-%m-%dT%H:%M:%SZ")

    gen = pd.DataFrame({"asset_id": asset_id, "ts_utc": ts_iso, "mwh_net": mwh_net.astype(float)})
    gen.to_sql("generation_hourly", engine, if_exists="append", index=False, chunksize=50_000)

    prices = pd.DataFrame({"ts_utc": ts_iso, "bidding_zone_id": zone, "price_eur_per_mwh": price.astype(float)})
    prices.to_sql("day_ahead_prices_hourly", engine, if_exists="append", index=False, chunksize=50_000)
