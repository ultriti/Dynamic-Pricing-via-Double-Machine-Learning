
from pathlib import Path
import pandas as pd

# Update this path after downloading the dataset.
DATA_PATH = Path("backend/data/raw/Online Retail.xlsx")


def inspect_dataset(path):
    if not path.exists():
        print(f"Dataset not found: {path}")
        print("Download the dataset and update DATA_PATH.")
        return

    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    print("\n--- Dataset Overview ---")
    print("Shape:", df.shape)
    print("\nColumns:")
    print(df.columns.tolist())

    print("\n--- Data Types ---")
    print(df.dtypes)

    print("\n--- Missing Values ---")
    print(df.isnull().sum())

    print("\n--- Duplicate Rows ---")
    print(df.duplicated().sum())

    print("\n--- Numeric Summary ---")
    print(df.describe(include="all").T)

    # Check common retail data-quality issues.
    for column in ["UnitPrice", "Quantity"]:
        if column in df.columns:
            print(f"\nInvalid {column} values (< = 0):")
            print((df[column] <= 0).sum())


if __name__ == "__main__":
    inspect_dataset(DATA_PATH)

