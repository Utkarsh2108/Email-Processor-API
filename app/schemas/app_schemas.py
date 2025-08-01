# app/schemas/app_schemas.py

from pydantic import BaseModel
from typing import List, Optional

class ProcessingResult(BaseModel):
    source_from: Optional[str] = None
    source_subject: Optional[str] = None
    status: str
    details: Optional[str] = None

class ProcessingReport(BaseModel):
    message: str
    processed_count: int
    sent_count: int
    results: List[ProcessingResult]