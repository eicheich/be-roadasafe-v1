from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ReportParameterResponse(BaseModel):
    nilai_L: float = Field(..., ge=0.0, le=100.0)
    nilai_K: float = Field(..., ge=0.0, le=100.0)
    nilai_P: float = Field(..., ge=0.0, le=100.0)
    nilai_T: float = Field(..., ge=0.0, le=100.0)

    model_config = ConfigDict(from_attributes=True)


class StatusLogResponse(BaseModel):
    id: int
    status_lama: str
    status_baru: str
    diubah_oleh: str
    catatan: Optional[str] = None
    waktu: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    id: int
    kode_laporan: Optional[str] = None
    lokasi_jalan: Optional[str] = None
    tipe_kerusakan: Optional[str] = "Lubang (Pothole)"
    estimasi_kedalaman_cm: Optional[float] = None
    device_id: Optional[str] = None
    latitude: float
    longitude: float
    akurasi_gps: float
    kecepatan: Optional[float] = None
    arah: Optional[float] = None
    waktu: datetime
    gambar_path: str
    confidence: float
    skor: float
    kategori: str
    status: str
    jumlah_terlapor: int
    versi_model: str
    created_at: datetime
    updated_at: datetime
    parameter: Optional[ReportParameterResponse] = None
    status_logs: List[StatusLogResponse] = []
    is_duplicate: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class ReportStatusUpdate(BaseModel):
    status: str  # Pending, Terverifikasi, Dalam Penanganan, Selesai, Ditolak
    catatan: Optional[str] = None


class ReportMapItem(BaseModel):
    id: int
    kode_laporan: Optional[str] = None
    lokasi_jalan: Optional[str] = None
    tipe_kerusakan: Optional[str] = None
    estimasi_kedalaman_cm: Optional[float] = None
    latitude: float
    longitude: float
    skor: float
    kategori: str
    status: str
    color: str  # green (#22c55e), yellow (#eab308), red (#ef4444)
    jumlah_terlapor: int
    waktu: datetime


class ReportSummaryResponse(BaseModel):
    total_laporan: int
    menunggu_verifikasi: int
    terverifikasi_ditangani: int
    selesai_ditambal: int
    ditolak: int
    urgensi: dict


class RecalculateResponse(BaseModel):
    recalculated_count: int
    message: str
