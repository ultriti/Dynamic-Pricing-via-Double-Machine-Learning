from pathlib import Path

import pandas as pd


# Project paths
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "shorya_online_retail_clean.csv"
)
OUTPUT_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "shorya_retail_features.csv"
)


def run_feature_engineering():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found: {DATA_PATH}"
        )

    print("Loading cleaned retail dataset...")
    df = pd.read_csv(DATA_PATH, low_memory=False)

    required_columns = [
        "StockCode",
        "InvoiceDate",
        "Quantity",
        "UnitPrice",
    ]

    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Prepare data types
    df["StockCode"] = df["StockCode"].astype("string")
    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"], errors="coerce"
    )
    df["Quantity"] = pd.to_numeric(
        df["Quantity"], errors="coerce"
    )
    df["UnitPrice"] = pd.to_numeric(
        df["UnitPrice"], errors="coerce"
    )

    # Remove invalid transactions and exclude returns
    df = df.dropna(
        subset=["StockCode", "InvoiceDate", "Quantity", "UnitPrice"]
    )
    df = df[
        (df["Quantity"] > 0)
        & (df["UnitPrice"] > 0)
        & (df["StockCode"].str.strip() != "")
    ].copy()

    if df.empty:
        raise ValueError("No valid transactions remain after cleaning.")

    # Calculate revenue if it is not already available
    if "Revenue" not in df.columns:
        df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    else:
        df["Revenue"] = pd.to_numeric(
            df["Revenue"], errors="coerce"
        )
        df = df.dropna(subset=["Revenue"])

    df["Date"] = df["InvoiceDate"].dt.normalize()

    # Keep products with at least 20 transaction lines
    product_counts = df.groupby("StockCode").size()
    selected_products = product_counts[product_counts >= 20].index

    df = df[df["StockCode"].isin(selected_products)].copy()

    if df.empty:
        raise ValueError(
            "No products have at least 20 transaction lines."
        )

    print(f"Products selected: {df['StockCode'].nunique()}")
    print("Aggregating daily product sales...")

    # Calculate daily demand, revenue and transaction-line count
    daily = (
        df.groupby(["StockCode", "Date"], as_index=False)
        .agg(
            daily_quantity=("Quantity", "sum"),
            daily_revenue=("Revenue", "sum"),
            daily_transaction_lines=("InvoiceDate", "size"),
        )
    )

    # Create a calendar for every selected product.
    # Dates with no sales will have zero demand.
    all_dates = pd.date_range(
        start=daily["Date"].min(),
        end=daily["Date"].max(),
        freq="D",
    )

    all_products = sorted(daily["StockCode"].unique())

    full_index = pd.MultiIndex.from_product(
        [all_products, all_dates],
        names=["StockCode", "Date"],
    )

    features = (
        daily.set_index(["StockCode", "Date"])
        .reindex(full_index)
        .reset_index()
    )

    # Fill dates without sales with zero
    value_columns = [
        "daily_quantity",
        "daily_revenue",
        "daily_transaction_lines",
    ]

    features[value_columns] = features[value_columns].fillna(0)

    features = features.sort_values(
        ["StockCode", "Date"]
    ).reset_index(drop=True)

    # Past-demand features (no future-data leakage)
    grouped_quantity = features.groupby("StockCode")["daily_quantity"]

    features["quantity_lag_1"] = grouped_quantity.shift(1)
    features["quantity_lag_7"] = grouped_quantity.shift(7)

    features["quantity_rolling_mean_7"] = (
        features.groupby("StockCode")["daily_quantity"]
        .transform(
            lambda values: values.shift(1).rolling(
                window=7, min_periods=3
            ).mean()
        )
    )

    # Calendar features
    features["day_of_week"] = features["Date"].dt.dayofweek
    features["day_of_month"] = features["Date"].dt.day
    features["month"] = features["Date"].dt.month
    features["is_weekend"] = (
        features["day_of_week"] >= 5
    ).astype(int)

    # Save feature-engineered dataset
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT_PATH, index=False)

    print("\nFeature engineering completed!")
    print(f"Rows created: {len(features):,}")
    print(f"Columns created: {len(features.columns)}")
    print(f"Date range: {all_dates.min().date()} to {all_dates.max().date()}")
    print(f"Output saved to: {OUTPUT_PATH}")
    print("\nPreview:")
    print(features.head())


if __name__ == "__main__":
    run_feature_engineering()