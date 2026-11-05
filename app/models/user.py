from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    peran = Column(String(20), default="pelapor", nullable=False)  # pelapor, admin, pengelola
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")

