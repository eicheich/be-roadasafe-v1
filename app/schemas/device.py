from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DeviceRegister(BaseModel):
    id: str  # Unique device identifier
    model_perangkat: Optional[str] = None
    versi_app: Optional[str] = None


class DeviceResponse(BaseModel):
    id: str
    user_id: Optional[int] = None
    model_perangkat: Optional[str] = None
    versi_app: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
