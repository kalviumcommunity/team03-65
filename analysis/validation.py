"""Day 18 — Dataset Validation and Error Handling Module.

Provides defensive validation for uploaded files, data structures, and analysis requests:
- Format verification (.csv only)
- Non-empty payload verification
- Required columns validation with remediation guidance
- Numeric typing and range sanitization
- Clean error/warning diagnostics for dashboard display without exposing raw Python tracebacks.
"""

from typing import Dict, List, Tuple, Any, Optional
import io
import pandas as pd
import numpy as np

from analysis.correlation import COLUMN_ALIASES, normalize_dataframe_columns

# Canonical required analytical columns (or their aliases)
CORE_REQUIRED_FIELDS = [
    "completion_rate",  # or completion_pct
    "watch_duration",   # or watch_duration_minutes
    "pause_count",
    "sessions_per_week",
    "retained"          # or retained_30d
]

class DatasetValidationError(Exception):
    """User-friendly dataset validation exception carrying structured diagnostic details."""
    def __init__(self, message: str, missing_columns: Optional[List[str]] = None, suggested_fix: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.missing_columns = missing_columns or []
        self.suggested_fix = suggested_fix or "Check your CSV format and ensure all required columns are present."

def validate_csv_upload(file_obj) -> Tuple[bool, str, Optional[pd.DataFrame]]:
    """Validate uploaded CSV file object or buffer.

    Returns:
        (is_valid: bool, error_or_success_message: str, parsed_df: Optional[pd.DataFrame])
    """
    if file_obj is None:
        return False, "No file was uploaded. Please select a CSV file.", None

    filename = getattr(file_obj, "name", "uploaded_file.csv")
    if not str(filename).lower().endswith(".csv"):
        return False, f"Unsupported file format '{filename}'. Only CSV files (.csv) are supported.", None

    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        df = pd.read_csv(file_obj)
    except pd.errors.EmptyDataError:
        return False, "The uploaded CSV file is empty. Please provide a file with valid headers and data records.", None
    except Exception as exc:
        return False, f"Failed to parse CSV file: {str(exc)}. Please verify file formatting.", None

    if df.empty or len(df) == 0:
        return False, "The uploaded dataset contains 0 records. Please upload a file with viewer activity records.", None

    # Check columns
    is_valid, msg, norm_df = validate_dataframe_schema(df)
    if not is_valid:
        return False, msg, None

    return True, f"Dataset successfully validated: {len(norm_df):,} records loaded.", norm_df

def validate_dataframe_schema(df: pd.DataFrame) -> Tuple[bool, str, pd.DataFrame]:
    """Validate that a DataFrame has required columns or aliases for analytics."""
    if df is None or df.empty:
        return False, "Dataset is empty. Cannot perform analysis on empty data.", pd.DataFrame()

    norm_df = normalize_dataframe_columns(df).copy()

    # Identify missing core fields
    missing_fields = []
    for field in CORE_REQUIRED_FIELDS:
        if field not in norm_df.columns:
            missing_fields.append(field)

    if missing_fields:
        fields_str = ", ".join(missing_fields)
        msg = (
            f"Dataset is missing required columns: [{fields_str}]. "
            "Supported column headers include: completion_rate (or completion_pct), "
            "watch_duration (or watch_duration_minutes), pause_count, sessions_per_week, and retained (or retained_30d)."
        )
        return False, msg, norm_df

    # Sanitize numeric fields
    for field in ["completion_rate", "watch_duration", "pause_count", "sessions_per_week"]:
        if field in norm_df.columns:
            norm_df[field] = pd.to_numeric(norm_df[field], errors="coerce").fillna(0.0)

    if "retained" in norm_df.columns:
        norm_df["retained"] = pd.to_numeric(norm_df["retained"], errors="coerce").fillna(0).astype(int)

    return True, "Schema valid", norm_df

def safe_run_analysis(analysis_func, *args, **kwargs) -> Dict[str, Any]:
    """Execute an analytical routine defensively, catching unexpected errors and returning a safe fallback payload."""
    try:
        result = analysis_func(*args, **kwargs)
        return {"success": True, "data": result, "error": None}
    except Exception as exc:
        return {
            "success": False,
            "data": None,
            "error": f"Analysis could not be completed: {str(exc)}"
        }
