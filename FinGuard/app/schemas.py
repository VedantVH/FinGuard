from typing import List, Optional, Dict
from pydantic import BaseModel

class Classification(BaseModel):
    intent: str  # greeting | smalltalk | finance_question | claim_to_check | not_finance
    claim_summary: str
    topics: List[str]
    region: Optional[str] = None
    risk_level: str  # low|medium|high
    action: str  # direct_answer | fact_check | refuse
    confidence: float

class SourceItem(BaseModel):
    source_name: str
    url: str
    source_type: str
    topic: str
    region: Optional[str] = None

class GenerationResult(BaseModel):
    reply: str
    verdict: str  # Likely True/False/Unverified/Context Needed/Avoid Advice