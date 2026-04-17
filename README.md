# ren-econ

Dummy-data demo for **10 German onshore wind** projects: DCF, 10-year PPA breakeven, per-project HTML dashboards, and a **portfolio `index.html`** with a map and table to pick a site.

## Quick start (easiest)

From **any directory**, run (uses **`python3`**, creates `.venv`, installs, seeds, builds **all** dashboards + `index.html`, opens the portfolio on macOS):

```bash
bash /path/to/ren_econ/scripts/bootstrap_dashboard.sh
```

Example clone path:

```bash
bash ~/Documents/git/test_ideas/ren_econ/scripts/bootstrap_dashboard.sh
```

Outputs live under **`dist/`** next to `pyproject.toml`:

- **`dist/index.html`** — map + **merit-order chart** (breakeven PPA, cheapest first) + table → links to each project
- **`dist/merit_order.html`** — same merit chart + ranked table (also written by `build-index`)
- **`dist/dashboard_DE_WIND_01.html`** … **`dist/dashboard_DE_WIND_10.html`** — same economics layout as before, one per asset

Regenerate merit order only (no need to rebuild every dashboard):

```bash
./.venv/bin/ren-econ merit-order --db data/wind_demo.sqlite --out dist/merit_order.html --hub-index index.html
```

### `zsh: command not found: ren-econ`

Use the venv executable (no `activate` required):

```bash
./.venv/bin/ren-econ seed --db data/wind_demo.sqlite
./.venv/bin/ren-econ build-index --db data/wind_demo.sqlite --out-dir dist
```

One project only (optional):

```bash
./.venv/bin/ren-econ build --db data/wind_demo.sqlite --asset DE_WIND_03 --out dist/dashboard_DE_WIND_03.html
```

Add `--hub-index index.html` if that file sits beside a portfolio index you already opened.

First-time setup:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
```

Module form:

```bash
./.venv/bin/python -m ren_econ build-index --db data/wind_demo.sqlite --out-dir dist
```

Open from the repo root (run **each** `open` on its **own line** — nothing after the path):

```bash
open dist/index.html
open dist/merit_order.html
```

### macOS `open`: “The files … `#`, `map`, `merit` … do not exist”

`open` treats **every word** after the path as **another file** to open. In **zsh**, `# text` at the end of a line is **not** a comment unless **`setopt interactivecomments`** is on — so a line like `open dist/index.html # map …` makes zsh try to open files named `#`, `map`, `merit`, etc.

**Fix:** put comments on the **previous** line, or enable comments:

```bash
setopt interactivecomments
# now inline comments work
```

Or always use **one command per line** with no trailing words (as in the block above).

## Manual steps

Use **`python3`** and **`python3 -m pip`**. Work in the **repository root** (directory with **`pyproject.toml`** — do not `cd` into the inner `ren_econ/` package folder).

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -e .
ren-econ seed --db data/wind_demo.sqlite
ren-econ build-index --db data/wind_demo.sqlite --out-dir dist
open dist/index.html
open dist/merit_order.html
```

### Toolchain check (optional)

```bash
python3 scripts/check_toolchain.py
```

## Data layout

SQLite tables:

- **`assets`** — one row per project (`asset_id`, name, lat/lon, MW, `bidding_zone_id` label, COD dates).
- **`generation_hourly`** — `(asset_id, ts_utc, mwh_net)`.
- **`day_ahead_prices_hourly`** — **`(asset_id, ts_utc, price_eur_per_mwh)`** — one wholesale **hourly curve per project** (node / capture style), joined to generation on `asset_id` + `ts_utc`.

Replace the SQLite file or point repositories at Postgres using the same column names.
