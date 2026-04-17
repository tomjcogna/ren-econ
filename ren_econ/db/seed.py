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
    asset_id TEXT NOT NULL,
    ts_utc TEXT NOT NULL,
    price_eur_per_mwh REAL NOT NULL,
    PRIMARY KEY (asset_id, ts_utc),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_gen_asset_ts ON generation_hourly (asset_id, ts_utc);
CREATE INDEX IF NOT EXISTS idx_price_asset_ts ON day_ahead_prices_hourly (asset_id, ts_utc);
"""

# Ten notional onshore sites across Germany (WGS84). Each row gets its own hourly wholesale curve.
DEMO_PROJECTS: list[dict] = [
    {
        "asset_id": "DE_WIND_01",
        "name": "Itzehoe Bight Onshore",
        "latitude": 53.92,
        "longitude": 9.72,
        "net_capacity_mw": 182.0,
        "price_base": 22.0,
        "cf_mean": 0.31,
        "season_phase": 0.0,
    },
    {
        "asset_id": "DE_WIND_02",
        "name": "Oldenburg Moor East",
        "latitude": 53.08,
        "longitude": 8.22,
        "net_capacity_mw": 165.0,
        "price_base": 23.5,
        "cf_mean": 0.29,
        "season_phase": 0.35,
    },
    {
        "asset_id": "DE_WIND_03",
        "name": "Ruppin Ridge",
        "latitude": 52.95,
        "longitude": 12.85,
        "net_capacity_mw": 220.0,
        "price_base": 21.0,
        "cf_mean": 0.27,
        "season_phase": 0.7,
    },
    {
        "asset_id": "DE_WIND_04",
        "name": "Jerichower Land Cluster",
        "latitude": 52.18,
        "longitude": 11.95,
        "net_capacity_mw": 138.0,
        "price_base": 24.8,
        "cf_mean": 0.30,
        "season_phase": 1.05,
    },
    {
        "asset_id": "DE_WIND_05",
        "name": "Egge Hills Wind",
        "latitude": 51.72,
        "longitude": 8.78,
        "net_capacity_mw": 128.0,
        "price_base": 26.2,
        "cf_mean": 0.26,
        "season_phase": 1.4,
    },
    {
        "asset_id": "DE_WIND_06",
        "name": "Pfälzerwald Edge",
        "latitude": 49.42,
        "longitude": 7.85,
        "net_capacity_mw": 196.0,
        "price_base": 25.0,
        "cf_mean": 0.28,
        "season_phase": 1.75,
    },
    {
        "asset_id": "DE_WIND_07",
        "name": "Rhön Uplands",
        "latitude": 50.52,
        "longitude": 9.78,
        "net_capacity_mw": 174.0,
        "price_base": 23.0,
        "cf_mean": 0.32,
        "season_phase": 2.1,
    },
    {
        "asset_id": "DE_WIND_08",
        "name": "Danube Forest Corridor",
        "latitude": 48.78,
        "longitude": 11.42,
        "net_capacity_mw": 208.0,
        "price_base": 20.5,
        "cf_mean": 0.25,
        "season_phase": 2.45,
    },
    {
        "asset_id": "DE_WIND_09",
        "name": "Hohenlohe Plateau",
        "latitude": 49.12,
        "longitude": 9.38,
        "net_capacity_mw": 186.0,
        "price_base": 24.2,
        "cf_mean": 0.29,
        "season_phase": 2.8,
    },
    {
        "asset_id": "DE_WIND_10",
        "name": "Schleswiger Geest",
        "latitude": 54.78,
        "longitude": 9.35,
        "net_capacity_mw": 200.0,
        "price_base": 22.8,
        "cf_mean": 0.33,
        "season_phase": 3.15,
    },
]


def write_demo_sqlite(path: Path) -> None:
    """
    Create SQLite with 10 German onshore wind projects and 25y of hourly generation + **per-asset**
    wholesale curves (`day_ahead_prices_hourly.asset_id`).
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

    zone = "DE_LU"
    asset_rows = []
    for i, p in enumerate(DEMO_PROJECTS):
        asset_rows.append(
            {
                "asset_id": p["asset_id"],
                "name": p["name"],
                "latitude": p["latitude"],
                "longitude": p["longitude"],
                "net_capacity_mw": p["net_capacity_mw"],
                "currency": "EUR",
                "bidding_zone_id": zone,
                "cod_date": "2026-01-01",
                "analysis_start_date": "2024-01-01",
                "construction_end_date": "2025-12-31",
            }
        )
    pd.DataFrame(asset_rows).to_sql("assets", engine, if_exists="append", index=False)

    start = pd.Timestamp("2026-01-01", tz="UTC")
    end = pd.Timestamp("2050-12-31 23:00", tz="UTC")
    hours = pd.date_range(start, end, freq="h", tz="UTC")
    n = len(hours)
    hour_of_year = ((hours.dayofyear - 1) * 24 + hours.hour).astype(int) % 8760
    ts_iso = hours.strftime("%Y-%m-%dT%H:%M:%SZ")

    for i, p in enumerate(DEMO_PROJECTS):
        aid = p["asset_id"]
        rng_g = np.random.default_rng(100 + i)
        rng_p = np.random.default_rng(200 + i)
        seasonal = 0.11 * np.sin(2 * np.pi * hour_of_year / 8760.0 + p["season_phase"])
        diurnal = 0.035 * np.sin(2 * np.pi * hours.hour / 24.0 + i * 0.2)
        noise_cf = rng_g.normal(0.0, 0.018, size=n)
        capacity_factor = np.clip(p["cf_mean"] - 0.02 + seasonal + diurnal + noise_cf, 0.02, 0.95)
        mwh_net = capacity_factor * p["net_capacity_mw"]

        base = p["price_base"]
        seasonal_p = 7.5 * np.sin(2 * np.pi * hour_of_year / 8760.0 + 0.7 + p["season_phase"])
        noise_p = rng_p.normal(0.0, 4.5, size=n)
        price = np.clip(base + seasonal_p + noise_p, 5.0, 200.0)

        gen = pd.DataFrame({"asset_id": aid, "ts_utc": ts_iso, "mwh_net": mwh_net.astype(float)})
        gen.to_sql("generation_hourly", engine, if_exists="append", index=False, chunksize=50_000)

        prices = pd.DataFrame(
            {"asset_id": aid, "ts_utc": ts_iso, "price_eur_per_mwh": price.astype(float)}
        )
        prices.to_sql("day_ahead_prices_hourly", engine, if_exists="append", index=False, chunksize=50_000)
