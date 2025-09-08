# %% setup
import os
import pandas as pd
import matplotlib.pyplot as plt
from helpers import open_remote_session, run_query

# %% quick test query
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
    run_query(conn, "SELECT COUNT(*) FROM users;", title="users")
    run_query(conn, "SELECT COUNT(*) FROM purchases;", title="purchases")

    ## User Type Counts with Bar Chart visual
    df_users = run_query(conn, """
                            SELECT user_type, COUNT(*) AS count
                            FROM users
                            GROUP BY user_type
                            ORDER BY count DESC;""", as_df=True)
    print(df_users)
    ## Top 10 spenders
    df_spenders = run_query(conn, """
                            SELECT first_name, last_name, total_spent
                            FROM users
                            ORDER BY total_spent DESC
                            LIMIT 10; """, as_df=True, limit = None)
    print(df_spenders)

    ## Device/browser distribution
    df_device = run_query(conn, """
              SELECT last_device, COUNT(*) as count
              FROM users
              GROUP BY last_device
              ORDER BY count DESC;""",as_df=True)
    print(df_device)
    ## Top 5 categories by revenue
    df_revenue= run_query(conn, """
              SELECT product_category, SUM(total_price) AS sum_total_price
              FROM purchases
              GROUP BY product_category
              ORDER BY sum_total_price DESC
              LIMIT 5;
              """,as_df=True)
    print(df_revenue)
    ## Monthly revenue trend (2023-2024)
    df_monthly = run_query(conn, """
              SELECT DATE_TRUNC('month', purchase_date)::date AS month,
              SUM(COALESCE(total_price, 0)) AS revenue
              FROM purchases
              WHERE EXTRACT(YEAR FROM purchase_date) = 2023
              OR EXTRACT(YEAR FROM purchase_date) =2024
              GROUP BY month
              ORDER BY month;""", as_df=True, limit =None)
    print(df_monthly)

    ## Plots
    ## Bar Chart: Revenue by category
    plt.figure(figsize=(8,5))
    plt.bar(df_revenue['product_category'], df_revenue['sum_total_price'])
    plt.title("Top 5 Categories by Revenue")
    plt.ylabel("Revenue")
    plt.xlabel("Category")
    plt.savefig("charts/bar_revenue_by_category.png")
    plt.close()

    ## Line Chart: Monthly Revenue
    plt.plot(df_monthly['month'],df_monthly['revenue'])
    plt.title("Revenue over time (Jan 2023-Dec 2024)")
    plt.xlabel("Date")
    plt.ylabel("Revenue")
    plt.savefig("charts/line_revenue_overtime")
    plt.close()

    ## Pie Chart: User types (%)
    plt.pie(df_users['count'], labels = df_users['user_type'])
    plt.title("Percentage of user type")
    plt.savefig("charts/pie_usertype_pct")
    plt.close()

    ## Histogram: Total Spending Distribution
    df_spenders = run_query(conn, """
    SELECT COALESCE(total_spent, 0) AS total_spent
    FROM users;""", as_df=True, limit=None)

    # visual
    plt.hist(df_spenders["total_spent"], bins=30, edgecolor="black")
    plt.xlabel("Total Spent")
    plt.ylabel("Number of users")
    plt.title("Distribution of Total Spending")
    plt.savefig("charts/hist_total_spending.png", dpi=140)
    plt.close()

    ## Pie chart of device distribution
    plt.pie(df_device['count'], labels = df_device['last_device'])
    plt.title("Percentage of device types")
    plt.savefig("charts/pie_devicetype_pct")
    plt.close()
    


    
