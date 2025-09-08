# simple_pipeline

Lightweight, reproducible ETL that stages CSVs on a remote host, loads into Postgres over an SSH tunnel, transforms them, and lets you run quick checks, analysis, and a simple ML baseline.

This README covers the pipeline scripts and SQL:
- `data_db_setup.ps1`
- `database_setup.sql`
- `transform_data.sql`
- `import_data.py`
- `db_conn.py`
- `helpers.py`

It follows the project spec (DB → Charts → Basic ML) and includes pointers to `data_analysis.py` and `ml_model.py` to complete the workflow.

## Quick start

1) Create a virtual environment and install dependencies

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Prepare remote data and database (unzips data, ensures DB exists/owned)

```powershell
.\data_db_setup.ps1
```

3) Apply schema, load CSVs, and run the transform

```powershell
python .\import_data.py `
	--apply-schema "database_setup.sql" `
	--apply-transform "transform_data.sql" `
	--clear-tables
```

4) Sanity-check counts and previews

```powershell
python .\db_conn.py
```

5) Analysis — `data_analysis.py`

```powershell
# Uses SSH tunnel + DB defaults; prints tables and saves charts
python .\data_analysis.py
```

6) ML model (baseline)

```powershell
# Trains one simple model and writes a summary to MODEL_RESULTS.md
python .\ml_model.py
```

## Prerequisites

- Windows/PowerShell or any OS with Python 3.10+ and `ssh/scp` available
- Python packages from `requirements.txt`
- A reachable SSH host with Postgres running locally on that host

Optional (password auth):

```powershell
$env:SSH_PASSWORD = "your-ssh-password"
```

## Configuration at a glance

- SSH flags: `--ssh-host`, `--ssh-user`, `--ssh-port`, `--ssh-password` (or `$env:SSH_PASSWORD`)
- DB flags: `--db-name`, `--db-user`, `--db-password`, `--db-port`
- Paths: `--remote-root` (default `/home/moxy/simple_pipeline`), `--users-subdir`, `--purchases-subdir`
- Logging: `--verbose` or `--quiet`

## 1) Prepare remote data and database — `data_db_setup.ps1`

What it does:
- Creates `~/simple_pipeline/data/user_data` and `~/simple_pipeline/data/purchase_data` on the remote host
- Copies `user_data.zip` and `purchase_data.zip` from the repo root and unzips them remotely
- Ensures the Postgres database exists and is owned by `appuser`

Run with defaults:

```powershell
# Defaults: user=moxy, host=10.10.219.8, remote base=~/simple_pipeline
# Expects ZIPs in the repo root: .\user_data.zip and .\purchase_data.zip
.\data_db_setup.ps1
```

Override parameters (example):

```powershell
.\data_db_setup.ps1 -User moxy -RemoteHost 10.10.219.8 -RemoteBase "~/simple_pipeline" -DbName ecommerce -DbOwner appuser
```

Note: This script prepares folders/data and DB ownership only. Tables are created by passing `--apply-schema` to the loader in the next step.

## 2) Database schema — `database_setup.sql`

Defines:
- Schema `raw` and staging tables `raw.users_raw`, `raw.purchases_raw` (text columns for CSV ingest)
- Final tables `public.users` and `public.purchases` with proper types/keys

Apply via the loader (next section) or manually with your SQL client.

## 3) Load and transform — `import_data.py` + `transform_data.sql`

`import_data.py` opens an SSH tunnel, streams remote CSVs into `raw.*`, and optionally applies schema and transform SQL.

Typical run (applies schema, loads CSVs, runs transform, and clears tables first):

```powershell
python .\import_data.py `
	--apply-schema "database_setup.sql" `
	--apply-transform "transform_data.sql" `
	--clear-tables
```

About `transform_data.sql`:
- Inserts from `raw.*` into `public.users` and `public.purchases` with type casts, null handling, and computed `total_price`

The 5 charts to produce (saved as PNG in `./charts/`):
- Revenue by category (bar)
- Monthly revenue 2023–2024 (line)
- User types (%) (pie)
- Total spending distribution (histogram)
- One of your choice (e.g., device types pie)

## 4) Quick checks — `db_conn.py`

Runs a few SELECTs and prints compact previews. Uses the same SSH/DB defaults (or your overrides).

```powershell
# If using password auth
$env:SSH_PASSWORD = "your-ssh-password"
python .\db_conn.py
```

## 5) Utilities — `helpers.py`

Small helpers used by the scripts:
- `open_remote_session(...)`: context manager that creates an SSH tunnel and a psycopg2 connection; can open SFTP
- `run_query(conn, sql, ...)`: executes SQL; prints a small table or returns a DataFrame (`as_df=True`)
- `execute_sql_text(conn, sql_text)`: splits on `;`, strips SQL comments, executes each statement in a transaction

## Outputs

- Charts in `./charts/`
	- `charts/bar_revenue_by_category.png`
	- `charts/line_revenue_overtime.png`
	- `charts/pie_usertype_pct.png`
	- `charts/hist_total_spending.png`
	- `charts/pie_devicetype_pct.png`
- Findings: `FINDINGS.md`
- Model summary: `MODEL_RESULTS.md`

## “Done” checklist

- PostgreSQL has `users` + `purchases` loaded with realistic row counts
- `data_analysis.py` produces required answers and 5 charts in `./charts/`
- `ml_model.py` trains one working model and logs results to `MODEL_RESULTS.md`
- Docs updated: setup, findings, model results, next ideas
- Re-runs cleanly from a fresh clone

## Defaults and notes

- Default SSH host/user: `10.10.219.8` / `moxy`
- Default DB: `ecommerce` with `appuser` / `devpassword`
- CSVs are expected on the remote under `~/simple_pipeline/data/{user_data,purchase_data}`
- Passwordless SSH with keys is supported; set `ssh_pkey` when using `open_remote_session` directly


