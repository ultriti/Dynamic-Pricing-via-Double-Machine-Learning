
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from io import BytesIO


app = FastAPI(title="EconoCausal API")

# Allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep the uploaded dataset in memory
dataset = None


# Check if the server is running
@app.get("/")
def home():
    return {"message": "EconoCausal API is running"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}

# ------------------------------------------
# Upload and validate the CSV dataset
@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    global dataset

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file")

    try:
        content = await file.read()
        df = pd.read_csv(BytesIO(content))
        df.columns = df.columns.str.strip()

        required_columns = [
            "recency", "history_segment", "history",
            "mens", "womens", "zip_code", "newbie",
            "channel", "segment", "visit",
            "conversion", "spend"
        ]

        missing_columns = [
            column for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise HTTPException(
                400,
                f"Missing columns: {missing_columns}"
            )

        dataset = df

        return {
            "message": "Dataset uploaded successfully",
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns),
            "missing_values": int(df.isnull().sum().sum()),
        }

    except pd.errors.EmptyDataError:
        raise HTTPException(400, "The uploaded CSV is empty")


# ------------------------------------------
# Return the first 10 rows of the dataset
@app.get("/api/dataset/preview")
def preview_dataset():
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    return {
        "rows": len(dataset),
        "columns": list(dataset.columns),
        "data": dataset.head(10).fillna("").to_dict(
            orient="records"
        ),
    }


# ------------------------------------------
# Return basic dataset statistics
@app.get("/api/dataset/summary")
def dataset_summary():
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    return {
        "total_customers": len(dataset),
        "total_columns": len(dataset.columns),
        "conversion_rate": round(
            float(dataset["conversion"].mean() * 100), 2
        ),
        "total_spend": round(float(dataset["spend"].sum()), 2),
        "avg_spend": round(float(dataset["spend"].mean()), 2),
        "visit_rate": round(
            float(dataset["visit"].mean() * 100), 2
        ),
        "treatment_groups": dataset["segment"].value_counts().to_dict(),
    }


# ------------------------------------------
# Return statistics for each column
@app.get("/api/dataset/columns")
def column_stats():
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    statistics = dataset.describe(include="all").fillna("").to_dict()

    return {"stats": statistics}


# ------------------------------------------
# Count the values in a selected column
@app.get("/api/dataset/value-counts/{column}")
def value_counts(column: str):
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    if column not in dataset.columns:
        raise HTTPException(400, f"Column '{column}' not found")

    counts = dataset[column].value_counts().to_dict()

    return {
        "column": column,
        "counts": {str(key): int(value) for key, value in counts.items()},
    }


# Return correlations between numeric columns
@app.get("/api/dataset/correlation")
def correlation_matrix():
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    correlation = dataset.corr(numeric_only=True).round(3)

    return {
        "columns": list(correlation.columns),
        "data": correlation.to_dict(),
    }


# Return histogram data for a selected column
@app.get("/api/dataset/distribution/{column}")
def distribution(column: str, bins: int = 20):
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    if column not in dataset.columns:
        raise HTTPException(400, f"Column '{column}' not found")

    values = dataset[column].dropna()

    # Group numeric values into histogram bins
    if pd.api.types.is_numeric_dtype(values):
        counts, edges = np.histogram(values, bins=bins)

        labels = [
            f"{round(edges[i], 2)}-{round(edges[i + 1], 2)}"
            for i in range(len(counts))
        ]

        return {
            "column": column,
            "type": "numeric",
            "labels": labels,
            "values": [int(count) for count in counts],
        }

    # Count occurrences of categorical values
    counts = values.value_counts()

    return {
        "column": column,
        "type": "categorical",
        "labels": [str(value) for value in counts.index.tolist()],
        "values": [int(count) for count in counts.values.tolist()],
    }


# Return sample data for a scatter plot
@app.get("/api/dataset/scatter")
def scatter_data(
    x: str = "history",
    y: str = "spend",
    sample: int = 500
):
    if dataset is None:
        raise HTTPException(404, "Please upload a dataset first")

    for column in [x, y]:
        if column not in dataset.columns:
            raise HTTPException(400, f"Column '{column}' not found")

    plot_data = dataset[[x, y]].dropna()

    if len(plot_data) > sample:
        plot_data = plot_data.sample(n=sample, random_state=42)

    return {
        "x_column": x,
        "y_column": y,
        "data": plot_data.to_dict(orient="records"),
    }
