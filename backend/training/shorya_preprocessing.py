
import pandas as pd
from pathlib import Path


def inspect_dataset(file_path):
    """Check a dataset for common data-quality issues."""

    df = pd.read_csv(file_path)

    # Clean whitespace from column names
    df.columns = df.columns.str.strip()

    print("Dataset shape:", df.shape)

    print("
Column names:")
    print(df.columns.tolist())

    print("
Missing values:")
    print(df.isnull().sum())

    print("
Duplicate rows:", df.duplicated().sum())

    print("
Data types:")
    print(df.dtypes)

    return df
