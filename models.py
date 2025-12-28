from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TeacherRequest(BaseModel):
    first_name: str
    last_name: str
    teacher_id: Optional[int] = None
    member_document_id: Optional[str] = None
    current_institution: Optional[str] = None
    field_of_study: Optional[str] = None


class ScrapedData(BaseModel):
    source: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    institution: Optional[str] = None
    authors: Optional[str] = None
    confidenceScore: float
    status: str = "pending"
    raw_data: dict = {}


class DataProposal(BaseModel):
    member: Optional[str | int] = None
    scrapedData: List[ScrapedData]
    createdAt: datetime
