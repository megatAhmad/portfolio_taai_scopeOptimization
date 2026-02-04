"""
Upload module for MWCS - handles file upload, validation, and schema detection.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

# Required columns for main dataset
REQUIRED_COLUMNS = [
    "Work ID",
    "Description",
    "Priority",
    "Category",
    "Estimated Hours",
    "Last Service Date",
]

# Optional columns for main dataset
OPTIONAL_COLUMNS = [
    "Asset ID",
    "Location",
    "Cost Estimate",
    "Risk Level",
    "Dependencies",
]


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_columns: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)


@dataclass
class UploadedData:
    """Container for uploaded data and metadata."""

    main_df: pd.DataFrame
    supporting_dfs: dict[str, pd.DataFrame] = field(default_factory=dict)
    filename: str = ""
    sheet_names: list[str] = field(default_factory=list)
    validation: Optional[ValidationResult] = None


class DataUploader:
    """Handles file upload, validation, and schema detection for MWCS."""

    def __init__(self, max_file_size_mb: int = 500):
        """Initialize the DataUploader."""
        self.max_file_size_mb = max_file_size_mb
        self._uploaded_data: Optional[UploadedData] = None

    @property
    def uploaded_data(self) -> Optional[UploadedData]:
        """Get the currently uploaded data."""
        return self._uploaded_data

    def load_excel(self, file_path: str) -> UploadedData:
        """Load an Excel file and detect its structure."""
        logger.info(f"Loading Excel file: {file_path}")

        # Load workbook to get sheet names
        workbook = load_workbook(file_path, read_only=True)
        sheet_names = workbook.sheetnames
        workbook.close()

        # Load main sheet (first sheet)
        main_df = pd.read_excel(file_path, sheet_name=0)
        logger.info(f"Loaded main sheet with {len(main_df)} rows")

        # Load supporting sheets
        supporting_dfs = {}
        for sheet_name in sheet_names[1:5]:  # Up to 5 supporting sheets
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if not df.empty:
                    supporting_dfs[sheet_name] = df
                    logger.info(f"Loaded supporting sheet '{sheet_name}' with {len(df)} rows")
            except Exception as e:
                logger.warning(f"Could not load sheet '{sheet_name}': {e}")

        # Create uploaded data container
        uploaded_data = UploadedData(
            main_df=main_df,
            supporting_dfs=supporting_dfs,
            filename=file_path,
            sheet_names=sheet_names,
        )

        # Validate the data
        uploaded_data.validation = self.validate(uploaded_data)
        self._uploaded_data = uploaded_data

        return uploaded_data

    def load_from_bytes(self, file_bytes: bytes, filename: str) -> UploadedData:
        """Load Excel data from bytes (for Streamlit file uploader)."""
        import io

        logger.info(f"Loading Excel from bytes: {filename}")

        # Load workbook to get sheet names
        workbook = load_workbook(io.BytesIO(file_bytes), read_only=True)
        sheet_names = workbook.sheetnames
        workbook.close()

        # Load main sheet (first sheet)
        main_df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0)
        logger.info(f"Loaded main sheet with {len(main_df)} rows")

        # Load supporting sheets
        supporting_dfs = {}
        for sheet_name in sheet_names[1:5]:  # Up to 5 supporting sheets
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
                if not df.empty:
                    supporting_dfs[sheet_name] = df
                    logger.info(f"Loaded supporting sheet '{sheet_name}' with {len(df)} rows")
            except Exception as e:
                logger.warning(f"Could not load sheet '{sheet_name}': {e}")

        # Create uploaded data container
        uploaded_data = UploadedData(
            main_df=main_df,
            supporting_dfs=supporting_dfs,
            filename=filename,
            sheet_names=sheet_names,
        )

        # Validate the data
        uploaded_data.validation = self.validate(uploaded_data)
        self._uploaded_data = uploaded_data

        return uploaded_data

    def validate(self, data: UploadedData) -> ValidationResult:
        """Validate uploaded data against required schema."""
        errors = []
        warnings = []

        # Get actual column names (case-insensitive matching)
        actual_columns = list(data.main_df.columns)
        actual_columns_lower = {col.lower(): col for col in actual_columns}

        # Check required columns
        missing_required = []
        for req_col in REQUIRED_COLUMNS:
            if req_col.lower() not in actual_columns_lower:
                missing_required.append(req_col)
                errors.append(f"Missing required column: {req_col}")

        # Check optional columns
        missing_optional = []
        for opt_col in OPTIONAL_COLUMNS:
            if opt_col.lower() not in actual_columns_lower:
                missing_optional.append(opt_col)
                warnings.append(f"Missing optional column: {opt_col}")

        # Check for empty dataset
        if data.main_df.empty:
            errors.append("Main dataset is empty")

        # Check for data quality issues
        if not data.main_df.empty:
            # Check for completely empty rows
            empty_rows = data.main_df.isna().all(axis=1).sum()
            if empty_rows > 0:
                warnings.append(f"Found {empty_rows} completely empty rows")

            # Check for duplicate Work IDs if column exists
            if "work id" in actual_columns_lower:
                work_id_col = actual_columns_lower["work id"]
                duplicates = data.main_df[work_id_col].duplicated().sum()
                if duplicates > 0:
                    warnings.append(f"Found {duplicates} duplicate Work IDs")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            detected_columns=actual_columns,
            missing_required=missing_required,
            missing_optional=missing_optional,
        )

    def get_preview(self, num_rows: int = 10) -> Optional[pd.DataFrame]:
        """Get a preview of the uploaded data."""
        if self._uploaded_data is None:
            return None
        return self._uploaded_data.main_df.head(num_rows)

    def get_column_stats(self) -> Optional[dict]:
        """Get statistics about each column in the main dataset."""
        if self._uploaded_data is None:
            return None

        stats = {}
        df = self._uploaded_data.main_df

        for col in df.columns:
            col_stats = {
                "dtype": str(df[col].dtype),
                "non_null_count": df[col].notna().sum(),
                "null_count": df[col].isna().sum(),
                "unique_count": df[col].nunique(),
            }

            # Add numeric stats if applicable
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats.update(
                    {
                        "min": df[col].min(),
                        "max": df[col].max(),
                        "mean": df[col].mean(),
                    }
                )

            stats[col] = col_stats

        return stats

    def normalize_columns(self) -> None:
        """Normalize column names to match expected schema."""
        if self._uploaded_data is None:
            return

        df = self._uploaded_data.main_df
        column_mapping = {}

        # Create mapping from actual to expected column names
        actual_columns_lower = {col.lower(): col for col in df.columns}

        all_expected = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
        for expected in all_expected:
            if expected.lower() in actual_columns_lower:
                actual = actual_columns_lower[expected.lower()]
                if actual != expected:
                    column_mapping[actual] = expected

        # Apply mapping
        if column_mapping:
            self._uploaded_data.main_df = df.rename(columns=column_mapping)
            logger.info(f"Normalized {len(column_mapping)} column names")

    def get_supporting_datasets(self) -> dict[str, pd.DataFrame]:
        """Get all supporting datasets."""
        if self._uploaded_data is None:
            return {}
        return self._uploaded_data.supporting_dfs

    def clear(self) -> None:
        """Clear the currently uploaded data."""
        self._uploaded_data = None
        logger.info("Cleared uploaded data")
