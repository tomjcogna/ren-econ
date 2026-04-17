# ren-econ

Dummy-data demo for an onshore wind discounted cash flow model with a 10-year PPA breakeven strike and an HTML dashboard.

## Quick start

```bash
cd ren_econ
python -m venv .venv && source .venv/bin/activate
pip install -e .
ren-econ build --db data/wind_demo.sqlite --out dist/dashboard.html
```

Open `dist/dashboard.html` in a browser.

## Data layout

SQLite tables mirror a production-style layout:

- `assets` — project metadata (WGS84 point, MW, COD).
- `generation_hourly` — `asset_id`, `ts_utc`, `mwh_net`.
- `day_ahead_prices_hourly` — `ts_utc`, `bidding_zone_id`, `price_eur_per_mwh`.

Replace the SQLite file or point repositories at Postgres using the same column names.
