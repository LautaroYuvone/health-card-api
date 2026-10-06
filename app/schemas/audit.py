from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AccessLogResponse(BaseModel):
    id: int
    practitioner_name: str
    practitioner_license: str
    practitioner_specialty: Optional[str] = None
    accessed_at: datetime
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)