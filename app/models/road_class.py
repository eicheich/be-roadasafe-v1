from sqlalchemy import Column, Integer, String, Float
from app.core.database import Base


class RoadClass(Base):
    __tablename__ = "road_classes"

    id = Column(Integer, primary_key=True, index=True)
    nama_jalan = Column(String(150), nullable=False, index=True)
    kelas = Column(String(50), nullable=False)  # arteri, kolektor, lokal
    bobot_kepadatan = Column(Float, nullable=False)  # arteri=100, kolektor=60, lokal=30

