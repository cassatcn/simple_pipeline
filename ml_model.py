# simple regression model

# get table of total purchases per email 

# option 1: predict total spend based on user type (maybe + last device)
# option 2: predict total spend in each category based on number of users in that category
# option 3: predict number of purchases per user based on user types (+ number of purchases, last device)

import os
import pandas as pd
import matplotlib.pyplot as plt
from helpers import open_remote_session, run_query

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor

import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error

# lets us use .env file for secrets
from dotenv import load_dotenv
load_dotenv()

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

    ## User Type Counts with Bar Chart visual
    df_users = run_query(conn, """
                            SELECT *
                            FROM users;""", as_df=True, limit = None)
    df_users.head()


    # plort scatter of total spend vs user type
    # import seaborn as sns
    # sns.scatterplot(data=df_users, x='email', y='total_spent', hue='user_type')
    # plt.xlabel('Email')
    # plt.ylabel('Total Spent')
    # plt.title('Total Spent by Email and User Type')
    #plt.show()

    print(len(df_users))

    df_users["total_spent"] = pd.to_numeric(df_users["total_spent"], errors="coerce")
    df_users["purchase_count"] = pd.to_numeric(df_users["purchase_count"], errors="coerce")

    # drop non feature rows
    df_users = df_users.drop(columns=["email", "first_name", "last_name"])

    # Separate features (X) and target (y)
    X = df_users.drop(columns=["total_spent"])
    y = df_users["total_spent"]

    # One-hot encode categorical variables (user_type, last_device)
    X = pd.get_dummies(X, drop_first=True)

    print("Feature columns after encoding:\n", X.head())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )   

    model = LinearRegression()
    model.fit(X_train, y_train)


    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("\nLinear Regression Model Evaluation:")
    print("Mean Squared Error:", mse)
    print("R² Score:", r2)

    # Actual vs Predicted
    plt.figure(figsize=(6,6))
    sns.scatterplot(x=y_test, y=y_pred)
    plt.plot([y_test.min(), y_test.max()],
            [y_test.min(), y_test.max()],
            'r--')  # 45-degree reference line
    plt.xlabel("Actual Spend")
    plt.ylabel("Predicted Spend")
    plt.title("Actual vs Predicted Spend")
    plt.savefig("charts/ml_actual_vs_predicted.png")
    plt.show()

    # Feature importance (coefficients)
    coef_df = pd.DataFrame({
        "Feature": X.columns,
        "Coefficient": model.coef_
    }).sort_values(by="Coefficient", ascending=False)

    plt.figure(figsize=(8,4))
    sns.barplot(x="Coefficient", y="Feature", data=coef_df)
    plt.title("Feature Importance (Linear Regression Coefficients)")
    plt.savefig("charts/ml_feature_importance.png")
    plt.show()


    # Train Gradient Boosting Regressor  
    gbr = GradientBoostingRegressor(random_state=42)          
    gbr.fit(X_train, y_train)                                 

    # Predict on test set  
    y_pred_gbr = gbr.predict(X_test)                          

    # Evaluate  
    mse_gbr = mean_squared_error(y_test, y_pred_gbr)         
    r2_gbr = r2_score(y_test, y_pred_gbr)                     
    print("\nGradient Boosting Regressor")                    
    print("---------------------------")                        
    print(f"MSE: {mse_gbr:.3f}")                              
    print(f"R^2: {r2_gbr:.3f}")     

    # Actual vs Predicted (GBR)  
    plt.figure()                                              
    plt.scatter(y_test, y_pred_gbr, alpha=0.7)                
    y_min, y_max = float(np.min(y_test)), float(np.max(y_test))  
    plt.plot([y_min, y_max], [y_min, y_max], linestyle="--")  
    plt.xlabel("Actual total_spent")                          
    plt.ylabel("Predicted total_spent")                       
    plt.title("Actual vs Predicted — Gradient Boosting")    
    plt.savefig("charts/ml_gbr_actual_predicted.png")  
    plt.show()                                                

    # Residuals vs Predicted (GBR)  
    res_gbr = y_test - y_pred_gbr                             
    plt.figure()                                              
    plt.scatter(y_pred_gbr, res_gbr, alpha=0.7)               
    plt.axhline(0, linestyle="--")                            
    plt.xlabel("Predicted total_spent (GBR)")                 
    plt.ylabel("Residuals (y - y_hat)")                       
    plt.title("Residuals vs Predicted — Gradient Boosting")   
    plt.savefig("charts/ml_gbr_residual_predicted.png")
    plt.show()                                                

    # Feature importance (GBR)  
    fi = pd.Series(gbr.feature_importances_, index=X_train.columns)  
    fi = fi.sort_values(ascending=True)                               
    plt.figure()                                                      
    plt.barh(fi.index, fi.values)                                     
    plt.xlabel("Feature Importance")                                  
    plt.title("Feature Importance — Gradient Boosting")     
    plt.savefig("charts/ml_gbr_feature_importance.png")           
    plt.tight_layout()                                                
    plt.show()








