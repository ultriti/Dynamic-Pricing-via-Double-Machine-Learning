
"""Analyze historical price-demand patterns in the Online Retail dataset."""

from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1]

DATA_PATH = (
    BACKEND_DIR
    / "data"
    / "processed"
    / "shorya_online_retail_clean.csv"
)

OUTPUT_DIR = BACKEND_DIR / "data" / "processed"


def run_analysis():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found: {DATA_PATH}\n"
            "Run shorya_retail_preprocessing.py first."
        )

    df = pd.read_csv(
        DATA_PATH,
        dtype={"InvoiceNo": "string", "StockCode": "string"},
        low_memory=False,
    )

    required_columns = {
        "StockCode",
        "Description",
        "Quantity",
        "UnitPrice",
        "Revenue",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # Convert numeric columns safely.
    for column in ["Quantity", "UnitPrice", "Revenue"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Keep valid positive sales records.
    df = df.dropna(
        subset=["StockCode", "Quantity", "UnitPrice", "Revenue"]
    )
    df = df[
        (df["Quantity"] > 0)
        & (df["UnitPrice"] > 0)
    ].copy()

    # Analyze products with at least 20 transaction lines.
    product_counts = df.groupby("StockCode")["Quantity"].transform("size")
    df = df[product_counts >= 20].copy()

    if df.empty:
        raise ValueError(
            "No products have at least 20 valid transaction lines."
        )

    # Summarize price, quantity, and revenue by product.
    product_summary = (
        df.groupby(["StockCode", "Description"], dropna=False)
        .agg(
            transaction_lines=("Quantity", "size"),
            average_unit_price=("UnitPrice", "mean"),
            median_unit_price=("UnitPrice", "median"),
            total_quantity=("Quantity", "sum"),
            average_quantity=("Quantity", "mean"),
            total_revenue=("Revenue", "sum"),
        )
        .reset_index()
    )

    # Calculate within-product correlation between price and quantity.
    # This is descriptive and does not prove causation.
    correlations = []

    for stock_code, group in df.groupby("StockCode"):
        if (
        group["UnitPrice"].nunique() < 2
        or group["Quantity"].nunique() < 2
    ):
            correlation = float("nan")
    else:
        correlation = group["UnitPrice"].corr(group["Quantity"])

        correlations.append(
            {
                "StockCode": stock_code,
                "price_quantity_correlation": correlation,
            }
        )
        valid_correlations = sum(
    pd.notna(item["price_quantity_correlation"])
    for item in correlations
)
    print(f"Products with valid correlations: {valid_correlations}")

    correlation_df = pd.DataFrame(correlations)

    product_summary = product_summary.merge(
        correlation_df,
        on="StockCode",
        how="left",
    )

    product_summary = product_summary.sort_values(
        "total_revenue",
        ascending=False,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / "shorya_price_demand_summary.csv"
    product_summary.to_csv(output_path, index=False)

    print("\n--- Price-Demand Analysis ---")
    print(f"Valid transaction lines analyzed: {len(df):,}")
    print(f"Unique products analyzed: {df['StockCode'].nunique():,}")

    print("\nTop 10 products by revenue:")
    print(product_summary.head(10).to_string(index=False))

    print(f"\nAnalysis saved to: {output_path}")
    print(
        "\nNote: Historical price-quantity correlations do not "
        "establish causal price effects."
    )


if __name__ == "__main__":
    run_analysis()
