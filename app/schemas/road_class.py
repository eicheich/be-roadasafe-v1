from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RoadClassCreate(BaseModel):
    nama_jalan: str
    kelas: str  # arteri, kolektor, lokal
    bobot_kepadatan: float = Field(..., ge=0.0, le=100.0)


class RoadClassResponse(BaseModel):
    id: int
    nama_jalan: str
    kelas: str
    bobot_kepadatan: float

    model_config = ConfigDict(from_attributes=True)
