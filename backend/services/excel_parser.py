"""
excel_parser.py
───────────────
Scans an Excel workbook for all tables, headers, and question codes.

Name normalisation:
  Converts "Table_1", "Table 1", "TABLE1", "table.1" → all → "table1"
  so that PPT references and Excel names always compare equal.

Supports both:
  1. Individual sheets per table (e.g. sheet named "Table 1", "Table 2"...)
  2. Single stacked sheet containing all tables (e.g. sheet named "All_Tables" or "TOC")
     with rows starting with "Table 1", "Table 2" etc.
"""

import re
from typing import List, Dict, Any

import openpyxl
import pandas as pd
import numpy as np

# ── openpyxl gradient fill stylesheet monkeypatch ────────────────────────────────
# Bypasses openpyxl crash: ValueError: Duplicate position 0.0
try:
    import openpyxl.styles.fills
    original_assign_position = openpyxl.styles.fills._assign_position

    def patched_assign_position(values):
        try:
            return original_assign_position(values)
        except ValueError:
            seen = set()
            deduped = []
            for val in values:
                if val.position not in seen:
                    seen.add(val.position)
                    deduped.append(val)
            return deduped

    openpyxl.styles.fills._assign_position = patched_assign_position
except Exception:
    pass


# ── Normalisation & Patterns ───────────────────────────────────────────────────
def normalize_name(name: str) -> str:
    """Lower-case, strip spaces / underscores / dots / dashes."""
    return re.sub(r"[\s_.\-]+", "", name.lower())


# Matches question codes like S1, A2, E5, F1, Q1a
Q_CODE_PATTERN = re.compile(r"\b([A-Za-z]{1,2}\d+[a-zA-Z]?)\b")
TABLE_START_RE = re.compile(r"^Table\s+(\d+)", re.IGNORECASE)


def deduplicate_cols(columns: List[str]) -> List[str]:
    """Ensure all column names are unique for pandas operations."""
    seen = {}
    new_cols = []
    for col in columns:
        col_str = str(col).strip()
        if col_str in seen:
            seen[col_str] += 1
            new_cols.append(f"{col_str}_{seen[col_str]}")
        else:
            seen[col_str] = 0
            new_cols.append(col_str)
    return new_cols


def _extract_question_codes(df: pd.DataFrame, super_idx: int) -> List[str]:
    """Find Q/S codes in rows before the super-header and in the first column."""
    codes = set()
    
    # 1. Search rows before the super-header
    search_limit = min(super_idx, len(df))
    for idx in range(search_limit):
        for val in df.iloc[idx].dropna():
            for m in Q_CODE_PATTERN.findall(str(val)):
                codes.add(m.upper())
                
    # 2. Search first column of the entire sheet
    for val in df.iloc[:, 0].dropna():
        for m in Q_CODE_PATTERN.findall(str(val)):
            codes.add(m.upper())
            
    return sorted(codes)


# ── Stacked table detector & parser ────────────────────────────────────────────
def _parse_stacked_sheet(sheet_name: str, file_path: str) -> List[Dict[str, Any]]:
    """Parse a stacked sheet containing multiple tables sequentially."""
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    
    table_boundaries = []
    current_table = None
    
    for idx, row in df.iterrows():
        val0 = row[0]
        if val0 is not None and not pd.isna(val0) and str(val0).strip() != "":
            val_str = str(val0).strip()
            match = TABLE_START_RE.match(val_str)
            if match:
                if current_table:
                    current_table["end_row"] = idx
                    table_boundaries.append(current_table)
                current_table = {
                    "table_name": val_str,
                    "start_row": idx,
                    "end_row": len(df)
                }
                
    if current_table:
        table_boundaries.append(current_table)
        
    tables = []
    for boundary in table_boundaries:
        name = boundary["table_name"]
        start = boundary["start_row"]
        end = boundary["end_row"]
        
        # Slice sub-dataframe for this table
        sub_df = df.iloc[start:end].reset_index(drop=True)
        
        # Extract title and question codes from first few rows of sub-df
        q_codes = set()
        title_text = ""
        if len(sub_df) > 1:
            title_row_val = sub_df.iloc[1, 0]
            if title_row_val is not None and not pd.isna(title_row_val):
                title_text = str(title_row_val).strip()
                for m in Q_CODE_PATTERN.findall(title_text):
                    q_codes.add(m.upper())
                    
        # Find super-header containing 'Total'
        super_idx = None
        for idx in range(len(sub_df)):
            row = sub_df.iloc[idx]
            if len(row) > 1 and str(row[1]).strip().lower() == 'total':
                super_idx = idx
                break
                
        if super_idx is None:
            continue
            
        super_header = list(sub_df.iloc[super_idx])
        
        # Find sub-header (first non-empty row after super_idx where col 1 is nan)
        sub_idx = None
        for idx in range(super_idx + 1, len(sub_df)):
            row = sub_df.iloc[idx]
            if row.dropna().empty:
                continue
            val_col1 = row[1]
            if val_col1 is not None and not pd.isna(val_col1) and str(val_col1).strip() != "":
                # We hit data row (contains total counts), so no sub-header exists
                break
            sub_idx = idx
            break
            
        sub_header = list(sub_df.iloc[sub_idx]) if sub_idx is not None else None
        
        # Forward fill super-header
        filled_super = []
        curr = None
        for val in super_header:
            if val is not None and not pd.isna(val) and str(val).strip() != "":
                curr = str(val).strip()
            filled_super.append(curr)
            
        # Build consolidated column names
        col_names = []
        for sup, sub in zip(filled_super, sub_header if sub_header else [None]*len(filled_super)):
            sup_str = str(sup) if sup is not None else ""
            sub_str = str(sub) if sub is not None and not pd.isna(sub) else ""
            
            if sup_str and sub_str:
                if sup_str.lower() in sub_str.lower() or sub_str.lower() in sup_str.lower():
                    col_name = sub_str
                else:
                    col_name = f"{sup_str} - {sub_str}"
            elif sup_str:
                col_name = sup_str
            elif sub_str:
                col_name = sub_str
            else:
                col_name = f"Col_{len(col_names)}"
            col_names.append(col_name)
            
        col_names[0] = "Label"
        col_names = deduplicate_cols(col_names)
        
        # Extract data rows
        start_data_idx = (sub_idx + 1) if sub_idx is not None else (super_idx + 1)
        data_df = sub_df.iloc[start_data_idx:].copy()
        data_df.columns = col_names
        
        # Clean rows
        data_df = data_df[data_df["Label"].notna()]
        data_df["Label"] = data_df["Label"].astype(str).str.strip()
        data_df = data_df[data_df["Label"] != ""]
        
        # Stop data collection before next Table starts or Sigma row
        cleaned_rows = []
        for idx, row in data_df.iterrows():
            lbl = str(row["Label"]).strip()
            if TABLE_START_RE.match(lbl) or lbl.lower() in ["sigma", "total"]:
                break
            cleaned_rows.append(row)
            
        if cleaned_rows:
            data_df = pd.DataFrame(cleaned_rows)
        else:
            data_df = pd.DataFrame(columns=col_names)
            
        # Convert numerical columns
        for col in col_names[1:]:
            data_df[col] = pd.to_numeric(
                data_df[col].astype(str).str.replace('%', '').str.strip(),
                errors='coerce'
            )
            
        record = {
            "sheet_name": sheet_name,
            "table_name": name,
            "normalized_name": normalize_name(name),
            "question_codes": list(q_codes),
            "row_count": len(data_df),
            "col_count": len(data_df.columns),
            "dataframe": data_df,
        }
        tables.append(record)
        
    return tables


# ── Single sheet parser ────────────────────────────────────────────────────────
def _scan_sheet_for_single_table(
    sheet_name: str,
    file_path: str,
) -> List[Dict[str, Any]]:
    """Parse a sheet containing a single table layout."""
    tables = []

    try:
        # Load sheet without headers
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        if df.empty:
            return []

        # Find the super-header index (contains 'Total' in col 1)
        super_idx = None
        for idx, row in df.iterrows():
            if len(row) > 1 and str(row[1]).strip().lower() == 'total':
                super_idx = idx
                break

        if super_idx is None:
            return []

        super_header = list(df.iloc[super_idx])

        # Find sub-header
        sub_idx = None
        for idx in range(super_idx + 1, len(df)):
            row = df.iloc[idx]
            if row.dropna().empty:
                continue
            val_col1 = row[1]
            if val_col1 is not None and not pd.isna(val_col1) and str(val_col1).strip() != "":
                break
            sub_idx = idx
            break

        sub_header = list(df.iloc[sub_idx]) if sub_idx is not None else None

        # Forward fill super-header
        filled_super = []
        curr = None
        for val in super_header:
            if val is not None and not pd.isna(val) and str(val).strip() != "":
                curr = str(val).strip()
            filled_super.append(curr)

        # Build consolidated column names
        col_names = []
        for sup, sub in zip(filled_super, sub_header if sub_header else [None]*len(filled_super)):
            sup_str = str(sup) if sup is not None else ""
            sub_str = str(sub) if sub is not None and not pd.isna(sub) else ""

            if sup_str and sub_str:
                if sup_str.lower() in sub_str.lower() or sub_str.lower() in sup_str.lower():
                    col_name = sub_str
                else:
                    col_name = f"{sup_str} - {sub_str}"
            elif sup_str:
                col_name = sup_str
            elif sub_str:
                col_name = sub_str
            else:
                col_name = f"Col_{len(col_names)}"
            col_names.append(col_name)

        col_names[0] = "Label"
        col_names = deduplicate_cols(col_names)

        # Extract data rows
        start_data_idx = (sub_idx + 1) if sub_idx is not None else (super_idx + 1)
        data_df = df.iloc[start_data_idx:].copy()
        data_df.columns = col_names

        # Clean row labels
        data_df = data_df[data_df["Label"].notna()]
        data_df["Label"] = data_df["Label"].astype(str).str.strip()
        data_df = data_df[data_df["Label"] != ""]
        data_df = data_df[~data_df["Label"].str.lower().isin(["sigma", "total"])]

        # Convert numerical columns
        for col in col_names[1:]:
            data_df[col] = pd.to_numeric(
                data_df[col].astype(str).str.replace('%', '').str.strip(),
                errors='coerce'
            )

        record = {
            "sheet_name": sheet_name,
            "table_name": sheet_name,
            "normalized_name": normalize_name(sheet_name),
            "question_codes": _extract_question_codes(df, super_idx),
            "row_count": len(data_df),
            "col_count": len(data_df.columns),
            "dataframe": data_df,
        }
        tables.append(record)

    except Exception:
        pass

    return tables


# ── Main entry ─────────────────────────────────────────────────────────────────
def parse_excel(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the Excel workbook.
    Returns a list of table records including their DataFrames.
    """
    xls = pd.ExcelFile(file_path)
    all_tables: List[Dict[str, Any]] = []

    for sheet_name in xls.sheet_names:
        s_name_lower = sheet_name.lower().strip()
        if s_name_lower in ["index", "toc"]:
            continue # Skip index/TOC sheets
            
        # Detect if it's a stacked table sheet
        # Check first column: if at least 2 cells match TABLE_START_RE, it is stacked
        try:
            temp_df = pd.read_excel(file_path, sheet_name=sheet_name, usecols=[0], header=None)
            matches = 0
            for val in temp_df[0].dropna():
                if TABLE_START_RE.match(str(val).strip()):
                    matches += 1
            is_stacked = (matches >= 2)
        except Exception:
            is_stacked = False
            
        if is_stacked:
            sheet_tables = _parse_stacked_sheet(sheet_name, file_path)
        else:
            sheet_tables = _scan_sheet_for_single_table(sheet_name, file_path)
            
        all_tables.extend(sheet_tables)

    return all_tables
