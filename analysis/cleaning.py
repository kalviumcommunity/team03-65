import numpy as np
import pandas as pd

NUMERIC_RULES = {
    "watch_duration": {"minimum": 0, "maximum": 1440, "integer": False},
    "completion_rate": {"minimum": 0, "maximum": 100, "integer": False},
    "pause_count": {"minimum": 0, "maximum": None, "integer": True},
    "sessions_per_week": {"minimum": 0, "maximum": 7, "integer": True},
}

BOOLEAN_VALUES = {
    "true": True,
    "1": True,
    "yes": True,
    "y": True,
    "false": False,
    "0": False,
    "no": False,
    "n": False,
}

def parse_boolean(val):
    """Safely convert different boolean representations into standard Python booleans."""
    if pd.isna(val):
        return None
    s = str(val).strip().lower()
    s = s.replace('"', '').replace("'", "").strip()
    return BOOLEAN_VALUES.get(s, None)

def get_data_diagnostics(df: pd.DataFrame) -> dict:
    """Analyze the raw dataframe to return stats on total, valid, and missing/invalid records."""
    total_records = len(df)
    if total_records == 0:
        return {
            "total_records": 0,
            "unique_users": 0,
            "unique_content_items": 0,
            "valid_records": 0,
            "missing_invalid_records": 0
        }

    # Start with all rows marked as valid (True)
    is_valid = pd.Series(True, index=df.index)

    # 1. Check user_id & content_id
    for col in ["user_id", "content_id"]:
        if col not in df.columns:
            is_valid[:] = False
        else:
            s_col = df[col].astype(str).str.strip().replace("nan", "")
            is_valid = is_valid & df[col].notna() & (s_col != "")

    # 2. Check numeric columns
    for col, rules in NUMERIC_RULES.items():
        if col not in df.columns:
            is_valid[:] = False
            continue
        
        # Convert to numeric. coerced to NaN if not convertible
        num_vals = pd.to_numeric(df[col], errors='coerce')
        
        # Check if is null
        col_valid = num_vals.notna()
        
        # Check minimum
        if rules["minimum"] is not None:
            col_valid = col_valid & (num_vals >= rules["minimum"])
            
        # Check maximum
        if rules["maximum"] is not None:
            col_valid = col_valid & (num_vals <= rules["maximum"])
            
        is_valid = is_valid & col_valid

    # 3. Check retained column
    if "retained" not in df.columns:
        is_valid[:] = False
    else:
        parsed_retained = df["retained"].apply(parse_boolean)
        is_valid = is_valid & parsed_retained.notna()

    valid_count = int(is_valid.sum())
    
    unique_users = 0
    unique_content_items = 0
    if "user_id" in df.columns:
        unique_users = int(df["user_id"].dropna().astype(str).str.strip().nunique())
    if "content_id" in df.columns:
        unique_content_items = int(df["content_id"].dropna().astype(str).str.strip().nunique())

    return {
        "total_records": total_records,
        "unique_users": unique_users,
        "unique_content_items": unique_content_items,
        "valid_records": valid_count,
        "missing_invalid_records": total_records - valid_count
    }

def clean_viewing_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return viewing data with consistent, API-safe cleaned values."""
    cleaned = df.copy()

    # 1. Clean user_id and content_id
    for column in ("user_id", "content_id"):
        cleaned[column] = cleaned[column].astype("string").str.strip()
        cleaned[column] = cleaned[column].replace("", pd.NA)
    cleaned = cleaned.dropna(subset=["user_id", "content_id"])

    # 2. Clean numeric columns
    for column, rules in NUMERIC_RULES.items():
        # Convert to numeric, coercing errors to NaN
        values = pd.to_numeric(cleaned[column], errors="coerce")
        values = values.replace([np.inf, -np.inf], np.nan)
        
        # Calculate median of valid values within the boundaries
        valid_mask = values.notna()
        if rules["minimum"] is not None:
            valid_mask = valid_mask & (values >= rules["minimum"])
        if rules["maximum"] is not None:
            valid_mask = valid_mask & (values <= rules["maximum"])
            
        valid_values = values[valid_mask]
        median = valid_values.median()
        
        # Fallback if no valid values at all
        fill_val = 0 if pd.isna(median) else median
        
        # Replace out-of-bounds/invalid values with the median
        invalid_mask = ~valid_mask
        values[invalid_mask] = np.nan
        values = values.fillna(fill_val)
        
        cleaned[column] = values.round().astype(int) if rules["integer"] else values.round(2)

    # 3. Clean retained column
    parsed_retained = cleaned["retained"].apply(parse_boolean)
    
    valid_retained = parsed_retained.dropna()
    if not valid_retained.empty:
        most_common = valid_retained.mode().iloc[0]
    else:
        most_common = False
        
    cleaned["retained"] = parsed_retained.fillna(most_common).astype(bool)

    # 4. Drop duplicate records
    return cleaned.drop_duplicates().reset_index(drop=True)
