import argparse
import io
import os
import posixpath
import logging
import warnings
from typing import Iterable, List
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings(
        "ignore",
        category=CryptographyDeprecationWarning,
        module=r"paramiko.*",
    )
except Exception:
    pass
import paramiko
import psycopg2
from helpers import execute_sql_text, open_remote_session

# Example usage:
# python .\import_data.py --apply-schema "database_setup.sql" --apply-transform "transform_data.sql" --clear-tables

logger = logging.getLogger(__name__)


def list_remote_csvs(sftp: paramiko.SFTPClient, directory: str) -> Iterable[str]:
    """Yield full remote paths for .csv files within a remote directory."""
    try:
        for entry in sftp.listdir_attr(directory):
            name = entry.filename
            if name.lower().endswith(".csv"):
                yield f"{directory.rstrip('/')}/{name}"
    except FileNotFoundError:
        logger.warning("[warn] directory not found on server: %s", directory)


def copy_csv_stream(
    cur: psycopg2.extensions.cursor,
    table: str,
    sftp: paramiko.SFTPClient,
    remote_path: str,
    *,
    encoding: str = "utf-8",
) -> None:
    """Stream a remote CSV file through COPY FROM STDIN into the given table."""
    with sftp.open(remote_path, "rb") as f_bin:
        f_txt = io.TextIOWrapper(f_bin, encoding=encoding, newline="")  # type: ignore[arg-type]
        sql = f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true)"
        cur.copy_expert(sql=sql, file=f_txt)


def _load_directory_into_table(
    conn: psycopg2.extensions.connection,
    sftp: paramiko.SFTPClient,
    directory: str,
    table: str,
    *,
    encoding: str = "utf-8",
) -> int:
    """Load all CSV files from a remote directory into the specified table."""
    logger.info("[load] scanning %s", directory)
    files: List[str] = sorted(list_remote_csvs(sftp, directory))
    if not files:
        logger.info("[load] no CSV files found in %s", directory)
        return 0

    loaded = 0
    with conn.cursor() as cur:
        for path in files:
            logger.info("[load] %s -> %s", path, table)
            copy_csv_stream(cur, table, sftp, path, encoding=encoding)
            loaded += 1
    conn.commit()
    logger.info("[load] %s done (%d file(s))", table, loaded)
    return loaded


def apply_sql_if_requested(
    conn: psycopg2.extensions.connection,
    sql_path: str | None,
    *,
    encoding: str = "utf-8",
    label: str = "sql",
) -> bool:
    """Apply a local SQL file if provided. Use `label` for log prefixes (e.g., 'schema' or 'transform')."""
    if not sql_path:
        return False

    if os.path.isfile(sql_path):
        with open(sql_path, "r", encoding=encoding) as f:
            sql_text = f.read()
        logger.info("[%s] applying local %s", label, sql_path)
        execute_sql_text(conn, sql_text)
        logger.info("[%s] applied", label)
        return True

    logger.warning("[%s] local file not found: %s; skipping.", label, sql_path)
    return False


def summarize_raw_counts(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    """Print and return counts for raw staging tables."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw.users_raw;")
        row = cur.fetchone()
        raw_users = int(row[0]) if row and row[0] is not None else 0
        cur.execute("SELECT COUNT(*) FROM raw.purchases_raw;")
        row = cur.fetchone()
        raw_purchases = int(row[0]) if row and row[0] is not None else 0
    logger.info("[summary] raw.users_raw rows: %d", raw_users)
    logger.info("[summary] raw.purchases_raw rows: %d", raw_purchases)
    return raw_users, raw_purchases


def summarize_public_counts(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    """Print and return counts for transformed public tables."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM public.users;")
        row = cur.fetchone()
        users = int(row[0]) if row and row[0] is not None else 0
        cur.execute("SELECT COUNT(*) FROM public.purchases;")
        row = cur.fetchone()
        purchases = int(row[0]) if row and row[0] is not None else 0
    logger.info("[summary] public.users rows: %d", users)
    logger.info("[summary] public.purchases rows: %d", purchases)
    return users, purchases


def truncate_raw_tables(conn: psycopg2.extensions.connection) -> None:
    """Truncate the raw staging tables used for loading."""
    logger.info("[raw] truncating raw tables…")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.users_raw, raw.purchases_raw;")
    conn.commit()


def truncate_public_tables(conn: psycopg2.extensions.connection) -> None:
    """Truncate the public target tables to avoid duplicate-key issues on re-runs."""
    logger.info("[public] truncating public tables…")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE public.purchases, public.users RESTART IDENTITY CASCADE;")
    conn.commit()

def main():
    ap = argparse.ArgumentParser(
        description="Stream remote CSVs into Postgres via SSH tunnel.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("--ssh-host", default=os.getenv("SSH_HOST", "10.10.219.8"))
    ap.add_argument("--ssh-user", default=os.getenv("SSH_USER", "moxy"))
    ap.add_argument("--ssh-port", type=int, default=int(os.getenv("SSH_PORT", "22")))
    ap.add_argument("--ssh-password", default=os.getenv("SSH_PASSWORD"))  # $env:SSH_PASSWORD="your-ssh-password"

    ap.add_argument("--db-user", default=os.getenv("DB_USER", "appuser"))
    ap.add_argument("--db-password", default=os.getenv("DB_PASSWORD", "devpassword"))
    ap.add_argument("--db-name", default=os.getenv("DB_NAME", "ecommerce"))
    ap.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "5432")))

    ap.add_argument("--remote-root", default=os.getenv("REMOTE_ROOT", "/home/moxy/simple_pipeline")) 
    ap.add_argument("--users-subdir", default="data/user_data")
    ap.add_argument("--purchases-subdir", default="data/purchase_data")

    ap.add_argument(
        "--clear-tables",
        action="store_true",
        help="TRUNCATE raw.* staging tables and public.* target tables before loading/transform.",
    )

    ap.add_argument("--apply-schema", metavar="SQL_FILE", help="Apply the given schema SQL file before loading.")
    ap.add_argument("--apply-transform", metavar="SQL_FILE", help="Run the given transform SQL file after loading.")

    verbosity = ap.add_mutually_exclusive_group()
    verbosity.add_argument("--verbose", action="store_true", help="Enable debug logging")
    verbosity.add_argument("--quiet", action="store_true", help="Show warnings and errors only")

    args = ap.parse_args()

    # Configure logging
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING
    logging.basicConfig(level=log_level, format="%(levelname)s %(message)s")

    remote_root = args.remote_root.rstrip("/")
    users_dir = posixpath.join(remote_root, args.users_subdir.strip("/"))
    purchases_dir = posixpath.join(remote_root, args.purchases_subdir.strip("/"))

    # Open combined session (DB tunnel + optional SFTP)
    with open_remote_session(
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_password=args.ssh_password,
        ssh_port=args.ssh_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_pass=args.db_password,
        db_port=args.db_port,
        want_sftp=True,
    ) as session:
        conn = session.conn
        sftp = session.sftp
        did_transform = False
        did_schema = False

        # Optional: apply schema DDL first
        did_schema = apply_sql_if_requested(
            conn, args.apply_schema, label="schema"
        )

        # Optional: clear both raw and public tables for a clean run
        if getattr(args, "clear_tables", False):
            truncate_public_tables(conn)
            truncate_raw_tables(conn)

        # Load users
        loaded_users = _load_directory_into_table(
            conn, sftp, users_dir, "raw.users_raw"
        )

        # Load purchases
        loaded_purchases = _load_directory_into_table(
            conn, sftp, purchases_dir, "raw.purchases_raw"
        )

        # Optional: run transform SQL
        did_transform = apply_sql_if_requested(
            conn, args.apply_transform, label="transform"
        )

        # Quick counts
        summarize_raw_counts(conn)

        if did_transform:
            summarize_public_counts(conn)

    logger.info("[done]")


if __name__ == "__main__":
    main()
