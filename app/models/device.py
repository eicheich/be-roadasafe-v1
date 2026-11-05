from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(100), primary_key=True, index=True)  # unique device identifier (UUID or Android ID)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    model_perangkat = Column(String(100), nullable=True)
    versi_app = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="devices")
    reports = relationship("Report", back_populates="device")

