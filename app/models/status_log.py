from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.time import now_wib


class StatusLog(Base):
    __tablename__ = "status_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    status_lama = Column(String(30), nullable=False)
    status_baru = Column(String(30), nullable=False)
    diubah_oleh = Column(String(100), nullable=False)
    catatan = Column(Text, nullable=True)
    waktu = Column(DateTime, default=now_wib, nullable=False)

    report = relationship("Report", back_populates="status_logs")

