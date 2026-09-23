from enum import Enum
from datetime import datetime

from pydantic import BaseModel
from uuid import UUID


class ScanType(str, Enum):
    SAST = "SAST"
    SCA = "SCA"
    SECRETS = "Secrets"
    CONTAINER_SECURITY = "Container Security"
    IAC = "IaC"
    DAST = "DAST"


class ScanUploadResponse(BaseModel):
    scan_id: UUID
    scan_type: ScanType
    tool: str
    filename: str
    status: str
    findings: int


class ScanHistoryItem(BaseModel):
    id: UUID
    scan_type: ScanType
    tool: str
    filename: str
    status: str
    uploaded_at: datetime
    findings: int
