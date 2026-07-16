from pydantic import BaseModel
from typing import List, Optional, Literal


class Instruction(BaseModel):
    id: int
    slide_number: int
    shape_id: int
    shape_name: str
    raw_text: str
    type: Literal["instruction", "symbol", "unknown"]
    left: float
    top: float
    width: float
    height: float
    hash: str


class InstructionsResponse(BaseModel):
    project_id: str
    instructions: List[Instruction]
    total: int


class ExcelTable(BaseModel):
    sheet_name: str
    table_name: str
    normalized_name: str
    question_codes: List[str]
    row_count: int
    col_count: int


class ExcelUploadResponse(BaseModel):
    status: str
    tables_detected: int
    normalized_names: List[str]


class MatchResult(BaseModel):
    instruction_id: int
    slide_number: int
    raw_text: str
    matched_table: Optional[str]
    match_confidence: Literal["exact", "fuzzy", "unmatched"]
    match_score: float


class ExtractResponse(BaseModel):
    status: str
    matches_found: int
    unmatched: int
    download_url: str


class MapPasteResponse(BaseModel):
    status: str
    charts_inserted: int
    symbols_handled: int
    download_url: str


class ProjectCreateResponse(BaseModel):
    project_id: str
    status: str
