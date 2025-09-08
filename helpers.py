# helpers.py

import textwrap, re
from typing import Any, Iterable, List, Optional, Sequence, Union
from contextlib import contextmanager
from types import SimpleNamespace
import os
from sshtunnel import SSHTunnelForwarder
import paramiko
import psycopg2

@contextmanager
def open_remote_session(
    *,
    ssh_host: str,
    ssh_user: str,
    db_name: str,
    db_user: str,
    db_pass: str,
    ssh_password: str | None = None,
    ssh_pkey: str | None = None,
    ssh_port: int = 22,
    db_port: int = 5432,
    want_sftp: bool = False,  # True for import_data, False for db_conn
):
    tunnel_kwargs = dict(
        ssh_username=ssh_user,
        remote_bind_address=("127.0.0.1", db_port),
        local_bind_address=("127.0.0.1", 0),
        set_keepalive=30,
    )
    if ssh_pkey:
        tunnel_kwargs["ssh_pkey"] = os.path.expanduser(ssh_pkey)
    else:
        tunnel_kwargs["ssh_password"] = ssh_password

    # SFTP client (optional)
    ssh_client = None
    sftp = None
    if want_sftp:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if ssh_pkey:
            pkey = paramiko.Ed25519Key.from_private_key_file(os.path.expanduser(ssh_pkey))
            ssh_client.connect(ssh_host, port=ssh_port, username=ssh_user, pkey=pkey)
        else:
            ssh_client.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)
        sftp = ssh_client.open_sftp()

    # Tunnel + DB connection
    with SSHTunnelForwarder((ssh_host, ssh_port), **tunnel_kwargs) as tunnel:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_pass,
            host="127.0.0.1",
            port=tunnel.local_bind_port,
            connect_timeout=10,
            options="-c statement_timeout=60000",
        )
        try:
            yield SimpleNamespace(conn=conn, sftp=sftp)
        finally:
            conn.close()
            if sftp:
                sftp.close()
            if ssh_client:
                ssh_client.close()

@contextmanager
def pg_conn_via_ssh(
    ssh_host: str,
    ssh_user: str,
    ssh_password: str,
    db_name: str,
    db_user: str,
    db_pass: str,
    ssh_port: int = 22,
    db_port: int = 5432,
):
    with open_remote_session(
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        ssh_password=ssh_password,
        db_name=db_name,
        db_user=db_user,
        db_pass=db_pass,
        ssh_port=ssh_port,
        db_port=db_port,
        want_sftp=False,
    ) as session:
        yield session.conn

def run_query(
    conn,
    sql: str,
    params: Optional[Union[Sequence[Any], dict]] = None,
    *,
    title: Optional[str] = None,
    limit: Optional[int] = 10,
    max_width: int = 36,
    autocommit: bool = True,
    as_df: bool = False,
    verbose: bool = True,
):
    do_print = verbose and not as_df

    with conn.cursor() as cur:
        cur.execute(sql, params)

        # No result set
        if cur.description is None:
            affected = cur.rowcount if cur.rowcount != -1 else None
            if autocommit:
                conn.commit()
            if do_print:
                label = f"[{title or _first_line(sql)}]"
                if affected is None:
                    print(f"{label} → executed.")
                else:
                    print(f"{label} → {affected} row(s) affected.")
                print()
            return affected

        # SELECT/RETURNING
        colnames = [d[0] for d in cur.description]
        rows = cur.fetchmany(limit) if limit else cur.fetchall()

        if as_df:
            return _to_df(rows, colnames)

        # Scalar 1x1
        if len(colnames) == 1 and len(rows) == 1:
            if do_print:
                label = f"[{title or colnames[0]}]"
                print(f"{label}: {rows[0][0]}")
                print()
            return rows[0][0]

        # Table preview
        if do_print:
            label = f"[{title or _first_line(sql)}]"
            print(label)

            def fmt(val: Any) -> str:
                s = "" if val is None else str(val)
                if max_width and max_width > 0 and len(s) > max_width:
                    s = s[: max_width - 1] + "…"
                return s

            display_rows = [[fmt(v) for v in r] for r in rows]
            widths = [
                max(len(str(colnames[i])), *(len(r[i]) for r in display_rows))
                if display_rows else len(str(colnames[i]))
                for i in range(len(colnames))
            ]

            def rowline(vals: Iterable[str]) -> str:
                return " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(vals))

            print(rowline(colnames))
            print("-+-".join("-" * w for w in widths))
            for r in display_rows:
                print(rowline(r))

            shown = len(rows)
            suffix = "" if limit is None else f" (showing up to {limit})"
            print(f"... {shown} row(s){suffix}")
            print()

        return rows

def _first_line(sql: str) -> str:
    return textwrap.shorten(sql.strip().splitlines()[0], width=60, placeholder="…")

def _to_df(rows: List[tuple], columns: List[str]):
    import pandas as pd
    return pd.DataFrame.from_records(rows, columns=columns)

def execute_sql_text(conn, sql_text: str):
    cleaned = _strip_sql_comments(sql_text)
    stmts = [s.strip() for s in cleaned.split(';') if s.strip()]
    with conn.cursor() as cur:
        for i, stmt in enumerate(stmts, 1):
            cur.execute(stmt)
    conn.commit()

def _strip_sql_comments(s: str) -> str:
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'--.*?$',    '', s, flags=re.M) 
    return s