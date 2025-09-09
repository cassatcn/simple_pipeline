# Model Results

# Linear Regression
### Why this model?
Simple, very interpretable baseline model. 

### Evaluation metrics
    - MSE: Penalizes larger errors more heavily. Lower is better, we have a high value of 29186500.09995478 (woah)
    - R Squared or coefficient of determination is the proportation of variance explained by the model. On a scale of 0 to 1, a 0.322 value means the model is not much better than just predicting the mean. 


### Visualizations

![Actual v Predicted](charts\ml_actual_vs_predicted.png)
This graph shows the models preformance on unseen data. exactly following the red line would mean perfect predictions. Our model's struggles with the high spenders
is very clear here. 



![Feature Importance](charts\ml_feature_importance.png)

This graph shows the importance of each feature we used in the model. Purchase count dominates, with the others marginally contributing. 
This indicates that spend is heavily proportional to amount of items purchased.


### Summary
Very mediocre at predicting spending, especially for higher spending users. Both models are limited by limited features imported (sorry, busy week).

# Gradient Boosting
### Why this model?
To see if a non linear pattern can be captured, we used gradient boosting regression. this is a decision tree type model that can usually capture complex relationships.


### Evaluation metrics
    - MSE: Penalizes larger errors more heavily. Lower is better, we have a high value of 29186500.09995478
    - R Squared or coefficient of determination is the proportation of variance explained by the model. On a scale of 0 to 1, a 0.323 value means the model is not much better than just predicting the mean. 




### Visualizations

![Actual v Predicted](charts\ml_gbr_actual_predicted.png)
This graph shows the models preformance on unseen data. exactly following the red line would mean perfect predictions. Our model's struggles with the high spenders
is very clear here. Overall, it doesn't look much different from the linear regression model. 



![Residuals](charts\ml_gbr_residual_predicted.png)
This graph shows the residuals- where the model over/under predicts. If the residuals are reandomly scattered around 0, the model is likely well calibrated. 
We get farther from zero as the spend amount gets higher. We need a key feature to get better at especially predicting the heavy spenders. 



![Feature Importance](charts\ml_gbr_feature_importance.png)
This graph shows the importance of each feature we used in the model. Purchase count dominates, stronger than in the Linear model.




# Summary
Overall, user type doesn't seem to have a big impact on predicting a user's spending. Purchase amount has a large impact. The relationship was not captured very well for high spenders with these predictors, loading in more of the features is reccommended. Another model that captures non linear relationships like random forest is also worth trying. 

