
from pathlib import Path
import pandas as pd

DATA_PATH = Path(
    "backend/data/processed/shorya_online_retail_clean.csv"
)


def run_eda():
   
    def run_eda():
        if not DATA_PATH.exists():
            raise FileNotFoundError(
            f"Cleaned dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(
        DATA_PATH,
        dtype={"InvoiceNo": "string", "StockCode": "string"},
        parse_dates=["InvoiceDate"],
        low_memory=False,
    )

    # Calculate daily revenue first.
    df["Date"] = df["InvoiceDate"].dt.date
    daily_revenue = (
        df.groupby("Date", as_index=False)["Revenue"]
        .sum()
        .sort_values("Date")
    )

    # Top products by total quantity sold.
    top_products = (
        df.groupby(["StockCode", "Description"], dropna=False)
        .agg(
            Quantity_Sold=("Quantity", "sum"),
            Revenue=("Revenue", "sum"),
        )
        .sort_values("Quantity_Sold", ascending=False)
        .head(10)
    )

    # Top countries by revenue.
    country_revenue = (
        df.groupby("Country", as_index=False)["Revenue"]
        .sum()
        .sort_values("Revenue", ascending=False)
        .head(10)
    )

    print("\n--- Dataset Summary ---")
    print("Rows:", len(df))
    print(
        "Date range:",
        df["InvoiceDate"].min(),
        "to",
        df["InvoiceDate"].max(),
    )

    print("\n--- Top 10 Products by Quantity ---")
    print(top_products.to_string())

    print("\n--- Top 10 Countries by Revenue ---")
    print(country_revenue.to_string(index=False))

    print("\n--- Daily Revenue Summary ---")
    print(daily_revenue["Revenue"].describe())

    output_dir = Path("backend/data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    daily_revenue.to_csv(
        output_dir / "shorya_daily_revenue.csv",
        index=False,
    )
    country_revenue.to_csv(
        output_dir / "shorya_country_revenue.csv",
        index=False,
    )

    print("\nEDA summaries saved to:", output_dir)


if __name__ == "__main__":
    run_eda()
