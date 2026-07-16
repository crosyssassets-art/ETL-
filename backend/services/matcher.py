"""
matcher.py
──────────
Matches PPT instructions to Excel tables using:
  1. Question-code direct lookup (high priority, handles typos like Table_9, A2)
  2. Exact normalised-name match (Table_1 ↔ Table 1)
  3. Fuzzy string match (rapidfuzz, threshold ≥ 75)
  4. Q-code match fallback

Returns a list of MatchResult dicts, each containing the matched DataFrame.
"""

import re
from typing import List, Dict, Any, Optional

from rapidfuzz import fuzz, process

from .excel_parser import normalize_name

# ── Extraction patterns ────────────────────────────────────────────────────────
TABLE_REF_PATTERN = re.compile(
    r"[Tt]able[\s_.]?(\d+[a-zA-Z]?)|[Tt]bl[\s_.]?(\d+[a-zA-Z]?)",
)
# Matches Q-codes like S1, A2, E5, F1, Q1a, etc.
Q_CODE_PATTERN = re.compile(r"\b([A-Za-z]{1,2}\d+[a-zA-Z]?)\b")
COLUMN_PATTERN = re.compile(r"[Cc]olumn\s*[-–:]\s*([A-Za-z\s]+)")

FUZZY_THRESHOLD = 75  # minimum similarity score


def _extract_table_ref(raw_text: str) -> Optional[str]:
    """Pull the first table reference from PPT raw text and normalise it."""
    m = TABLE_REF_PATTERN.search(raw_text)
    if m:
        num = m.group(1) or m.group(2)
        return normalize_name(f"Table{num}")
    return None


def _extract_q_codes(raw_text: str) -> List[str]:
    return [m.upper() for m in Q_CODE_PATTERN.findall(raw_text)]


def _extract_column(raw_text: str) -> Optional[str]:
    m = COLUMN_PATTERN.search(raw_text)
    return m.group(1).strip() if m else None


# ── Main matcher ───────────────────────────────────────────────────────────────
def match_instructions(
    instructions: List[Dict[str, Any]],
    excel_tables: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    For each PPT instruction, attempt to find the best-matching Excel table.
    Returns a list of match result dicts (one per instruction).
    """
    # Build lookup maps
    norm_to_table: Dict[str, Dict] = {t["normalized_name"]: t for t in excel_tables}
    all_norm_names: List[str] = list(norm_to_table.keys())

    results = []

    for instr in instructions:
        raw_text = instr["raw_text"]
        instr_type = instr["type"]

        # Symbols: no table matching needed
        if instr_type == "symbol":
            results.append({
                **instr,
                "matched_table": None,
                "matched_table_data": None,
                "match_confidence": "unmatched",
                "match_score": 0.0,
                "matched_column": None,
                "matched_q_codes": [],
            })
            continue

        table_ref = _extract_table_ref(raw_text)
        q_codes = _extract_q_codes(raw_text)
        column = _extract_column(raw_text)
        
        matched_table = None
        confidence = "unmatched"
        score = 0.0

        # Step 1: Question-code direct unique lookup (highest priority to handle typos)
        if q_codes:
            matching_tables = []
            for tbl in excel_tables:
                if any(qc in tbl["question_codes"] for qc in q_codes):
                    matching_tables.append(tbl)
            if len(matching_tables) == 1:
                matched_table = matching_tables[0]
                confidence = "exact"
                score = 100.0

        # Step 2: Exact match on normalised table reference (e.g. Table_1 -> table1)
        if matched_table is None and table_ref and table_ref in norm_to_table:
            matched_table = norm_to_table[table_ref]
            confidence = "exact"
            score = 100.0

        # Step 3: Fuzzy match on table reference
        if matched_table is None and table_ref and all_norm_names:
            best = process.extractOne(
                table_ref, all_norm_names, scorer=fuzz.ratio
            )
            if best and best[1] >= FUZZY_THRESHOLD:
                matched_table = norm_to_table[best[0]]
                confidence = "fuzzy"
                score = float(best[1])

        # Step 4: Q-code match fallback (if multiple tables have the Q-code)
        if matched_table is None and q_codes:
            for tbl in excel_tables:
                if any(qc in tbl["question_codes"] for qc in q_codes):
                    matched_table = tbl
                    confidence = "fuzzy"
                    score = 60.0
                    break

        # Extract relevant DataFrame slice if matched
        matched_df = None
        if matched_table is not None:
            df = matched_table.get("dataframe")
            if df is not None:
                if column:
                    # Look for exact or case-insensitive column match
                    col_normalized = normalize_name(column)
                    matching_cols = [c for c in df.columns if normalize_name(str(c)) == col_normalized]
                    
                    # If not found, try substring matching (e.g., "Total" in "Gender - Total")
                    if not matching_cols:
                        matching_cols = [c for c in df.columns if col_normalized in normalize_name(str(c))]
                        
                    if matching_cols:
                        # Keep the Label column for context + the matched column(s)
                        cols_to_keep = ["Label"] + matching_cols
                        # deduplicate while keeping order
                        cols_to_keep = list(dict.fromkeys(cols_to_keep))
                        matched_df = df[cols_to_keep].to_dict(orient="list")
                    else:
                        # Fallback to entire table
                        matched_df = df.to_dict(orient="list")
                else:
                    # Return entire table
                    matched_df = df.to_dict(orient="list")

        results.append({
            **instr,
            "matched_table": matched_table["table_name"] if matched_table else None,
            "matched_sheet": matched_table["sheet_name"] if matched_table else None,
            "matched_table_data": matched_df,
            "match_confidence": confidence,
            "match_score": score,
            "matched_column": column,
            "matched_q_codes": q_codes,
        })

    return results
