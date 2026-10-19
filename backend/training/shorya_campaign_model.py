
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "raw" / "marketing_campaign_dataset.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

df = pd.read_csv(DATA_PATH)

# Basic data cleaning
df.columns = df.columns.str.strip()
df = df.drop_duplicates()

# Clean numeric fields stored as text
df["Acquisition_Cost"] = (
    df["Acquisition_Cost"]
    .astype(str)
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
)
df["Acquisition_Cost"] = pd.to_numeric(
    df["Acquisition_Cost"], errors="coerce"
)

df["Duration"] = pd.to_numeric(
    df["Duration"].astype(str).str.replace(" days", "", regex=False),
    errors="coerce"
)

# Predict campaign ROI
target = "ROI"
drop_cols = ["ROI", "Campaign_ID", "Date"]

X = df.drop(columns=drop_cols, errors="ignore")
y = pd.to_numeric(df[target], errors="coerce")

# Remove rows where target is missing or invalid
valid = y.notna()
X, y = X.loc[valid], y.loc[valid]

numeric_cols = X.select_dtypes(include="number").columns.tolist()
categorical_cols = X.select_dtypes(exclude="number").columns.tolist()

numeric_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
    ("numeric", numeric_pipeline, numeric_cols),
    ("categorical", categorical_pipeline, categorical_cols)
])

model = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    ))
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model.fit(X_train, y_train)
predictions = model.predict(X_test)

print("Rows used:", len(df))
print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))
print("MAE:", round(mean_absolute_error(y_test, predictions), 4))
print("RMSE:", round(mean_squared_error(y_test, predictions) ** 0.5, 4))
print("R2:", round(r2_score(y_test, predictions), 4))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
import joblib
joblib.dump(model, OUTPUT_DIR / "shorya_campaign_roi_model.joblib")
print("Model saved to:", OUTPUT_DIR / "shorya_campaign_roi_model.joblib")
