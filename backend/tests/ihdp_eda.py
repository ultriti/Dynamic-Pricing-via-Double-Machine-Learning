import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Generating synthetic IHDP dataset...")
# Create fake data that looks like IHDP
np.random.seed(42)
n_samples = 747
X = np.random.randn(n_samples, 25)
t = np.random.randint(0, 2, n_samples) # Treatment (0 or 1)
y = X[:, 0] * 2 + t * 1.5 + np.random.randn(n_samples) # Outcome

df = pd.DataFrame(X, columns=[f'x_{i}' for i in range(25)])
df['t'] = t
df['y'] = y

print("\n--- First 5 rows of the dataset ---")
print(df.head())

print("\n--- Dataset Info ---")
print(df.info())

print("\n--- Checking for missing values ---")
print(df.isnull().sum().sum(), "missing values found.")

# Plotting
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
df['t'].value_counts().plot(kind='bar', ax=axes[0], color=['blue', 'orange'])
axes[0].set_title('Treatment Distribution')
df['y'].plot(kind='hist', ax=axes[1], bins=20, color='green')
axes[1].set_title('Outcome Distribution')

plt.tight_layout()
plt.savefig('ihdp_eda_plot.png')
print("\nEDA complete! A plot has been saved as 'ihdp_eda_plot.png'")