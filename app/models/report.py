from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    kode_laporan = Column(String(50), unique=True, index=True, nullable=True)  # Contoh: #RS-2026-0892
    lokasi_jalan = Column(String(200), nullable=True, index=True)  # Contoh: Jl. Pajajaran No. 45, Bogor Tengah
    tipe_kerusakan = Column(String(100), default="Lubang (Pothole)", nullable=False)
    estimasi_kedalaman_cm = Column(Float, nullable=True)  # Contoh: 8.5 cm
    device_id = Column(String(100), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    akurasi_gps = Column(Float, nullable=False)
    kecepatan = Column(Float, nullable=True)
    arah = Column(Float, nullable=True)
    waktu = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    gambar_path = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    skor = Column(Float, nullable=False)
    kategori = Column(String(20), nullable=False, index=True)  # Low, Medium, High
    status = Column(String(30), default="Pending", nullable=False, index=True)  # Pending, Terverifikasi, Dalam Penanganan, Selesai, Ditolak
    jumlah_terlapor = Column(Integer, default=1, nullable=False)
    versi_model = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    device = relationship("Device", back_populates="reports")
    parameter = relationship("ReportParameter", back_populates="report", uselist=False, cascade="all, delete-orphan")
    status_logs = relationship("StatusLog", back_populates="report", cascade="all, delete-orphan", order_by="StatusLog.waktu.desc()")


class ReportParameter(Base):
    __tablename__ = "report_parameters"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    nilai_L = Column(Float, nullable=False)  # Luas Area Kerusakan (0-100)
    nilai_K = Column(Float, nullable=False)  # Rasio Kedalaman/Bentuk (0-100)
    nilai_P = Column(Float, nullable=False)  # Posisi pada Jalur (0-100)
    nilai_T = Column(Float, nullable=False)  # Kepadatan Lalu Lintas (0-100)

    report = relationship("Report", back_populates="parameter")

