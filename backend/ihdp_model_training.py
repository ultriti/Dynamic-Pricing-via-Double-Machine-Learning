import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

print("Generating synthetic data for training...")
np.random.seed(42)
n_samples = 747
X = np.random.randn(n_samples, 25)
t = np.random.randint(0, 2, n_samples)
y = X[:, 0] * 2 + t * 1.5 + np.random.randn(n_samples)

df = pd.DataFrame(X, columns=[f'x_{i}' for i in range(25)])
df['t'] = t
df['y'] = y

# Split data
X_train, X_test, y_train, y_test = train_test_split(df.drop(columns=['y']), df['y'], test_size=0.2, random_state=42)

print("Training Random Forest Model...")
model = RandomForestRegressor(n_estimators=50, random_state=42) # 50 trees is fast
model.fit(X_train, y_train)

predictions = model.predict(X_test)
mse = mean_squared_error(y_test, predictions)

print(f"Model Training Complete!")
print(f"Mean Squared Error: {mse:.4f}")