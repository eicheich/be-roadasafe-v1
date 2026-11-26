from sqlalchemy import Column, Integer, Float, String, DateTime
from app.core.database import Base
from app.utils.time import now_wib


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    bobot_L = Column(Float, default=0.35, nullable=False)  # Luas area
    bobot_K = Column(Float, default=0.25, nullable=False)  # Kedalaman/bentuk
    bobot_P = Column(Float, default=0.20, nullable=False)  # Posisi pada jalur
    bobot_T = Column(Float, default=0.20, nullable=False)  # Kepadatan lalu lintas
    
    ambang_low = Column(Float, default=33.0, nullable=False)     # 0-33 -> Low
    ambang_medium = Column(Float, default=66.0, nullable=False)  # 34-66 -> Medium, >66 -> High
    
    versi_model_aktif = Column(String(50), default="yolov8n-pothole-v1.0", nullable=False)
    updated_at = Column(DateTime, default=now_wib, onupdate=now_wib)

