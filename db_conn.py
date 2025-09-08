# db_conn.py

import warnings
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except Exception:
    pass

import os
from helpers import open_remote_session, run_query


with open_remote_session(
    ssh_host="10.10.219.8",
    ssh_user="moxy",
    ssh_password=os.environ["SSH_PASSWORD"],  # $env:SSH_PASSWORD="your-ssh-password"
    db_name="ecommerce",
    db_user="appuser",
    db_pass="devpassword",
    want_sftp=False,
) as session:
    conn = session.conn

    # Example queries
    run_query(conn, "SELECT COUNT(*) FROM raw.users_raw;", title="raw.users_raw")
    run_query(conn, "SELECT COUNT(*) FROM raw.purchases_raw;", title="raw.purchases_raw")
    run_query(conn, "SELECT COUNT(*) FROM users;", title="users")
    run_query(conn, "SELECT COUNT(*) FROM purchases;", title="purchases")

    run_query(conn, "SELECT * FROM users LIMIT 5;", title="Sample users", limit=5)
    run_query(conn, """
        SELECT user_type, COUNT(*) AS n
        FROM users
        GROUP BY user_type
        ORDER BY n DESC;
    """, title="Users by type", limit=20)

    run_query(conn, """
        SELECT product_category, COUNT(*) AS n
        FROM purchases
        GROUP BY product_category
        ORDER BY n DESC;
    """, title="Top categories", limit=15)

    run_query(conn, """
        SELECT purchase_date, COUNT(*) AS orders
        FROM purchases
        GROUP BY purchase_date
        ORDER BY purchase_date
        LIMIT 15;
    """, title="First 15 days")

    # Saving as a pandas DataFrame and explicitly printing
    df_users = run_query(conn, "SELECT * FROM users LIMIT 5;", as_df=True)
    print(df_users)