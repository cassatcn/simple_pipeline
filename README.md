# simple_pipeline

Lightweight ETL demo that moves CSVs into Postgres over an SSH tunnel, transforms them, and lets you run quick checks.

This README only covers:
- `data_db_setup.ps1`
- `database_setup.sql`
- `transform_data.sql`
- `import_data.py`
- `db_conn.py`
- `helpers.py`

It follows the included project specification (DB → Charts → Basic ML) and adds brief placeholders for the analysis and ML steps to guide the rest of the work.

## Quick Start (spec-aligned)

1) Setup Python env

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Prepare remote data and DB (unzips and ensures DB exists)

```powershell
.\data_db_setup.ps1
```

3) Apply schema, load CSVs, and run transform

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

5) Analysis (placeholder)

```powershell
# Generates 5 charts to .\charts\ and summarizes findings in FINDINGS.md
python .\data_analysis.py
```

6) ML model (placeholder)

```powershell
# Trains ONE simple model and writes summary to MODEL_RESULTS.md
python .\ml_model.py
```

Outputs expected by spec:
- Charts saved in `./charts/`
- Findings in `FINDINGS.md`
- Model summary in `MODEL_RESULTS.md`

## Prereqs

- Python 3.10+ with packages from `requirements.txt`.
- A reachable SSH host with Postgres running locally on that host.
- Your PowerShell session set with the SSH password env var when needed.

Optional setup (run in PowerShell):

```powershell
# create and activate venv (optional)
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# set the SSH password for scripts that use password auth
$env:SSH_PASSWORD = "your-ssh-password"
```

## 1) Prepare remote data and database — `data_db_setup.ps1`

What it does:
- Creates `~/simple_pipeline/data/user_data` and `~/simple_pipeline/data/purchase_data` on the remote host.
- Copies `user_data.zip` and `purchase_data.zip` from the repository root to the remote base dir and unzips them.
- Ensures the Postgres database exists and is owned by `appuser`.

Requirements on the remote machine: `ssh/scp` access and `unzip` installed; may prompt for sudo.

Run:

```powershell
# Uses defaults: user=moxy, host=10.10.219.8, remote base=~/simple_pipeline
# Expects ZIPs next to this script in the repo root: .\user_data.zip and .\purchase_data.zip
.\data_db_setup.ps1
```

You can override parameters (examples):

```powershell
.\data_db_setup.ps1 -User moxy -RemoteHost 10.10.219.8 -RemoteBase "~/simple_pipeline" -DbName ecommerce -DbOwner appuser
```

If you prefer the previous approach (ZIPs in the Downloads folder), pass explicit paths:

```powershell
.\data_db_setup.ps1 `
	-LocalUserZip "$env:USERPROFILE\Downloads\user_data.zip" `
	-LocalPurchaseZip "$env:USERPROFILE\Downloads\purchase_data.zip"
```

Notes:
- The script only prepares remote directories/data and enforces DB ownership. Table creation happens when you pass `--apply-schema` to the loader below.

## 2) Database schema — `database_setup.sql`

Defines:
- Schema `raw` and staging tables `raw.users_raw`, `raw.purchases_raw` (all text columns for easy CSV ingest).
- Final tables `public.users` and `public.purchases` with proper types/keys.

Apply it either via the loader (next section) or manually using your preferred SQL client.

## 3) Load and transform — `import_data.py` + `transform_data.sql`

`import_data.py` opens an SSH tunnel, streams remote CSVs into `raw.*`, and optionally applies schema/transform SQL.

Typical run (applies schema, loads CSVs, runs transform, and clears tables first):

```powershell
python .\import_data.py `
	--apply-schema "database_setup.sql" `
	--apply-transform "transform_data.sql" `
	--clear-tables
```

Useful flags (all optional; have sensible defaults):
- SSH: `--ssh-host`, `--ssh-user`, `--ssh-port`, `--ssh-password` (or `$env:SSH_PASSWORD`)
- DB: `--db-name`, `--db-user`, `--db-password`, `--db-port`
- Paths: `--remote-root` (default `/home/moxy/simple_pipeline`), `--users-subdir`, `--purchases-subdir`
- Logging: `--verbose` or `--quiet`

About `transform_data.sql`:
- Inserts from `raw.*` into `public.users` and `public.purchases` with type casts, null-handling, and computed `total_price`.

Per spec, the analysis should answer:
- User type counts, Top 10 spenders, Device/browser distribution, Top 5 categories by revenue, Monthly revenue trend (2023–2024).

The 5 charts to produce (saved as PNG in `./charts/`):
- Revenue by category (bar), Monthly revenue 2023–2024 (line), User types (%) (pie), Total spending distribution (histogram), plus one of your choice.

## 4) Quick checks — `db_conn.py`

Runs a few SELECTs and prints tabular previews. Requires the same SSH/DB defaults or overrides.

Run:

```powershell
$env:SSH_PASSWORD = "your-ssh-password"  # if using password auth
python .\db_conn.py
```

## 5) Utilities — `helpers.py`

Contains small helpers used by the scripts:
- `open_remote_session(...)`: context manager that creates an SSH tunnel and a psycopg2 connection; optionally opens SFTP.
- `run_query(conn, sql, ...)`: executes SQL, prints compact tables, or returns pandas DataFrame with `as_df=True`.
- `execute_sql_text(conn, sql_text)`: splits on `;`, strips SQL comments, and executes each statement in a transaction.

## “Done” Checklist (from spec)

- PostgreSQL has `users` + `purchases` loaded with realistic row counts.
- `data_analysis.py` produces required answers and 5 charts in `./charts/`.
- `ml_model.py` trains ONE working model and logs results to `MODEL_RESULTS.md`.
- Documentation updated: setup, findings, model results, next ideas.
- Re-runs cleanly from a fresh clone.

## Defaults and notes

- Default SSH host/user: `10.10.219.8` / `moxy`.
- Default DB: `ecommerce` with `appuser` / `devpassword` (change for real usage).
- CSVs are expected on the remote under `~/simple_pipeline/data/{user_data,purchase_data}`.
- Passwordless SSH with keys is supported; set `ssh_pkey` when using `open_remote_session` directly.


