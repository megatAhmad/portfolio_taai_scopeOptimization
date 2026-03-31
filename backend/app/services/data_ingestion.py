import pandas as pd
import os
import json

def ingest_dataset_profile(file_path: str) -> dict:
    """
    Reads a CSV or Excel file, extracts columns, row count, 
    null rates, and distinct counts, and returns a schema dictionary.
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext == ".csv":
        df = pd.read_csv(file_path, nrows=5000) # Read sample for profile
        total_rows = sum(1 for line in open(file_path)) - 1
    elif file_ext in [".xls", ".xlsx"]:
        df = pd.read_excel(file_path, nrows=5000)
        # For Excel, we might just use the sample count as we can't efficiently count all lines
        total_rows = len(pd.read_excel(file_path, usecols=[0]))
    else:
        raise ValueError("Unsupported file format")

    columns = []
    for col in df.columns:
        null_count = df[col].isnull().sum()
        columns.append({
            "name": col,
            "type": str(df[col].dtype),
            "null_rate": float(null_count / len(df)) if len(df) > 0 else 0,
            "sample_values": df[col].dropna().head(3).tolist()
        })
        
    return {
        "total_rows": total_rows,
        "columns": columns
    }
