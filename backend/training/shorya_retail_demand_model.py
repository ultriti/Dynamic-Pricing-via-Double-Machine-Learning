
from pathlib import Path

import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score


BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "shorya_retail_features.csv"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "shorya_retail_demand_predictions.csv"
)


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {DATA_PATH}"
        )

    print("Loading feature-engineered dataset...")
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])

    required = [
        "StockCode",
        "Date",
        "daily_quantity",
        "quantity_lag_1",
        "quantity_lag_7",
        "quantity_rolling_mean_7",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
    ]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Sort chronologically before splitting
    df = df.sort_values(["Date", "StockCode"]).copy()

    # Predict demand using information available before that day.
    feature_columns = [
        "quantity_lag_1",
        "quantity_lag_7",
        "quantity_rolling_mean_7",
        "day_of_week",
        "day_of_month",
        "month",
        "is_weekend",
    ]

    df = df.dropna(subset=["quantity_lag_1"]).copy()

    # Use earlier dates for training and later dates for testing
    unique_dates = sorted(df["Date"].unique())
    split_index = int(len(unique_dates) * 0.8)

    if split_index <= 0 or split_index >= len(unique_dates):
        raise ValueError("Not enough dates for train/test split.")

    split_date = unique_dates[split_index]

    train = df[df["Date"] < split_date].copy()
    test = df[df["Date"] >= split_date].copy()

    X_train = train[feature_columns]
    y_train = train["daily_quantity"]

    X_test = test[feature_columns]
    y_test = test["daily_quantity"]

    print(f"Training rows: {len(train):,}")
    print(f"Testing rows: {len(test):,}")
    print(f"Test period starts: {pd.Timestamp(split_date).date()}")

    # Baseline: predict the average training demand
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(X_train, y_train)
    baseline_predictions = baseline.predict(X_test)

    # Model: Random Forest regression
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
    )
    print("Training Random Forest model...")
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    baseline_mae = mean_absolute_error(y_test, baseline_predictions)
    baseline_rmse = mean_squared_error(
        y_test, baseline_predictions
    ) ** 0.5
    baseline_r2 = r2_score(y_test, baseline_predictions)

    model_mae = mean_absolute_error(y_test, predictions)
    model_rmse = mean_squared_error(y_test, predictions) ** 0.5
    model_r2 = r2_score(y_test, predictions)

    print("\n--- Baseline Results ---")
    print(f"MAE:  {baseline_mae:.4f}")
    print(f"RMSE: {baseline_rmse:.4f}")
    print(f"R2:   {baseline_r2:.4f}")

    print("\n--- Random Forest Results ---")
    print(f"MAE:  {model_mae:.4f}")
    print(f"RMSE: {model_rmse:.4f}")
    print(f"R2:   {model_r2:.4f}")

    if model_mae < baseline_mae:
        print("\nThe model improved on the baseline MAE.")
    else:
        print("\nThe model did not improve on baseline MAE.")

    if model_r2 > baseline_r2:
        print("Random Forest improved on baseline R2.")
    else:
        print("Random Forest did not improve on baseline R2.")
    results = test[["StockCode", "Date", "daily_quantity"]].copy()
    results = results.rename(
        columns={"daily_quantity": "actual_quantity"}
    )
    results["predicted_quantity"] = predictions
    results["baseline_prediction"] = baseline_predictions

    results.to_csv(OUTPUT_PATH, index=False)

    print(f"\nPredictions saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
