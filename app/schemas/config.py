from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ConfigUpdate(BaseModel):
    bobot_L: Optional[float] = Field(None, ge=0.0, le=1.0)
    bobot_K: Optional[float] = Field(None, ge=0.0, le=1.0)
    bobot_P: Optional[float] = Field(None, ge=0.0, le=1.0)
    bobot_T: Optional[float] = Field(None, ge=0.0, le=1.0)
    ambang_low: Optional[float] = Field(None, ge=0.0, le=100.0)
    ambang_medium: Optional[float] = Field(None, ge=0.0, le=100.0)
    versi_model_aktif: Optional[str] = None


class ConfigResponse(BaseModel):
    id: int
    bobot_L: float
    bobot_K: float
    bobot_P: float
    bobot_T: float
    ambang_low: float
    ambang_medium: float
    versi_model_aktif: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
