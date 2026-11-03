
from pathlib import Path
import pandas as pd

RAW_PATH = Path("backend/data/raw/Online Retail.xlsx")
OUTPUT_PATH = Path("backend/data/processed/shorya_online_retail_clean.csv")


def preprocess_retail_data():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {RAW_PATH}")

    df = pd.read_excel(RAW_PATH, parse_dates=["InvoiceDate"])

    initial_rows = len(df)

    # Normalize column names and text values.
    df.columns = df.columns.str.strip()

    for col in ["Description", "Country", "StockCode", "InvoiceNo"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Remove exact duplicate records.
    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    # Remove rows missing essential transaction information.
    required = [
        "InvoiceNo",
        "StockCode",
        "InvoiceDate",
        "Quantity",
        "UnitPrice",
    ]
    df = df.dropna(subset=required).copy()

    # Keep positive sales transactions for this modeling dataset.
    # Negative quantities can represent returns/cancellations.
    # Non-positive prices are not valid for this simple sales analysis.
    invalid_quantity = int((df["Quantity"] <= 0).sum())
    invalid_price = int((df["UnitPrice"] <= 0).sum())

    df = df[
        (df["Quantity"] > 0) &
        (df["UnitPrice"] > 0)
    ].copy()

    # Add transaction-level revenue.
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]

    # CustomerID and Description may be missing, so preserve rows
    # and do not invent customer identities or product descriptions.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print("--- Preprocessing Summary ---")
    print("Initial rows:", initial_rows)
    print("Exact duplicates removed:", duplicate_count)
    print("Rows with non-positive quantity before filtering:", invalid_quantity)
    print("Rows with non-positive price before filtering:", invalid_price)
    print("Final rows:", len(df))
    print("Final columns:", df.columns.tolist())
    print("Remaining missing values:")
    print(df.isna().sum())
    print("Cleaned data saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    preprocess_retail_data()
