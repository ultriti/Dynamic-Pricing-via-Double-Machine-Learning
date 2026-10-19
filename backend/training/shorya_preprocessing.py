
import pandas as pd
from pathlib import Path


def inspect_dataset(file_path):
    """Check a dataset for common data-quality issues."""

    df = pd.read_csv(file_path)

    # Clean whitespace from column names
    df.columns = df.columns.str.strip()

    # Clean whitespace from text columns
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()

    # Remove exact duplicate rows
    duplicates_before = df.duplicated().sum()
    print("Duplicate rows before cleaning:", duplicates_before)

    df = df.drop_duplicates()

    print("Duplicate rows removed:", duplicates_before - df.duplicated().sum())
    print("Dataset shape after duplicate removal:", df.shape)


    # Display dataset information
    print("Dataset shape:", df.shape)
    print("Column names:")
    print(df.columns.tolist())
    print("Missing values:")
    print(df.isnull().sum())
    print("Duplicate rows:", df.duplicated().sum())
    print("Data types:")
    print(df.dtypes)

    return df
if __name__ == "__main__":
    base_path = Path("data/raw")

    datasets = [
        base_path / "marketing_campaign_dataset.csv",
        base_path / "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
    ]

    for file_path in datasets:
        if file_path.exists():
            print("Checking:", file_path.name)
            cleaned_df = inspect_dataset(file_path)

            output_path = Path("data/processed") / f"cleaned_{file_path.name}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cleaned_df.to_csv(output_path, index=False)

            print("Cleaned dataset saved to:", output_path)
        else:
            print("Dataset not found:", file_path)