# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# import pandas as pd
# from io import BytesIO

# app = FastAPI(title="EconoCausal API")

# # Allow React frontend to connect
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Store uploaded dataset in memory
# dataset = None


# @app.get("/")
# def home():
#     return {"message": "EconoCausal API is running"}


# @app.get("/api/health")
# def health():
#     return {"status": "healthy"}


# @app.post("/api/dataset/upload")
# async def upload_dataset(file: UploadFile = File(...)):
#     global dataset

#     if not file.filename.lower().endswith(".csv"):
#         raise HTTPException(
#             status_code=400,
#             detail="Please upload a CSV file"
#         )

#     try:
#         content = await file.read()
#         df = pd.read_csv(BytesIO(content))

#         required_columns = [
#             "recency",
#             "history_segment",
#             "history",
#             "mens",
#             "womens",
#             "zip_code",
#             "newbie",
#             "channel",
#             "segment",
#             "visit",
#             "conversion",
#             "spend",
#         ]

#         # Clean column names
#         df.columns = df.columns.str.strip()

#         missing_columns = [
#             col for col in required_columns
#             if col not in df.columns
#         ]

#         if missing_columns:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Missing columns: {missing_columns}"
#             )

#         dataset = df

#         return {
#             "message": "Dataset uploaded successfully",
#             "filename": file.filename,
#             "rows": len(df),
#             "columns": list(df.columns),
#             "missing_values": int(df.isnull().sum().sum()),
#         }

#     except pd.errors.EmptyDataError:
#         raise HTTPException(
#             status_code=400,
#             detail="The uploaded CSV is empty"
#         )


# @app.get("/api/dataset/preview")
# def preview_dataset():
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     return {
#         "rows": len(dataset),
#         "columns": list(dataset.columns),
#         "data": dataset.head(10).fillna("").to_dict(
#             orient="records"
#         ),
#     }


# @app.get("/api/dataset/summary")
# def dataset_summary():
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     return {
#         "total_customers": len(dataset),
#         "total_columns": len(dataset.columns),
#         "conversion_rate": round(
#             float(dataset["conversion"].mean() * 100), 2
#         ),
#         "total_spend": round(
#             float(dataset["spend"].sum()), 2
#         ),
#         "avg_spend": round(
#             float(dataset["spend"].mean()), 2
#         ),
#         "visit_rate": round(
#             float(dataset["visit"].mean() * 100), 2
#         ),
#         "treatment_groups": dataset["segment"].value_counts().to_dict(),
#     }


# @app.get("/api/dataset/columns")
# def column_stats():
#     """Return per-column statistics (describe) for numeric columns."""
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     desc = dataset.describe(include="all").fillna("").to_dict()
#     return {"stats": desc}


# @app.get("/api/dataset/value-counts/{column}")
# def value_counts(column: str):
#     """Return value counts for a given column."""
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     if column not in dataset.columns:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Column '{column}' not found"
#         )

#     counts = dataset[column].value_counts().to_dict()
#     # Convert keys to strings for JSON
#     counts = {str(k): int(v) for k, v in counts.items()}
#     return {"column": column, "counts": counts}


# @app.get("/api/dataset/correlation")
# def correlation_matrix():
#     """Return correlation matrix for numeric columns."""
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     corr = dataset.corr(numeric_only=True).round(3)
#     return {
#         "columns": list(corr.columns),
#         "data": corr.to_dict(),
#     }


# @app.get("/api/dataset/distribution/{column}")
# def distribution(column: str, bins: int = 20):
#     """Return histogram data for a numeric column."""
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     if column not in dataset.columns:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Column '{column}' not found"
#         )

#     import numpy as np
#     col_data = dataset[column].dropna()

#     if pd.api.types.is_numeric_dtype(col_data):
#         counts_arr, bin_edges = np.histogram(col_data, bins=bins)
#         labels = [
#             f"{round(bin_edges[i], 2)}-{round(bin_edges[i+1], 2)}"
#             for i in range(len(counts_arr))
#         ]
#         return {
#             "column": column,
#             "type": "numeric",
#             "labels": labels,
#             "values": [int(c) for c in counts_arr],
#         }
#     else:
#         vc = col_data.value_counts()
#         return {
#             "column": column,
#             "type": "categorical",
#             "labels": [str(l) for l in vc.index.tolist()],
#             "values": [int(v) for v in vc.values.tolist()],
#         }


# @app.get("/api/dataset/scatter")
# def scatter_data(x: str = "history", y: str = "spend", sample: int = 500):
#     """Return scatter plot data for two columns (sampled)."""
#     if dataset is None:
#         raise HTTPException(
#             status_code=404,
#             detail="Please upload a dataset first"
#         )

#     for col in [x, y]:
#         if col not in dataset.columns:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Column '{col}' not found"
#             )

#     df_sample = dataset[[x, y]].dropna()
#     if len(df_sample) > sample:
#         df_sample = df_sample.sample(n=sample, random_state=42)

#     return {
#         "x_column": x,
#         "y_column": y,
#         "data": df_sample.to_dict(orient="records"),
#     }

