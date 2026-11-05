from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.report import Report
from app.utils.geo import haversine_distance
from app.core.config import settings


class DeduplicationService:
    @staticmethod
    def find_duplicate_report(
        db: Session,
        latitude: float,
        longitude: float,
        radius_meters: float = settings.DEDUPLICATION_RADIUS_METERS
    ) -> Optional[Report]:
        """
        Mencari apakah ada laporan lubang jalan sebelumnya dalam radius toleransi (10-15 meter)
        yang statusnya masih aktif (bukan Selesai atau Ditolak).
        """
        # Estimasi bounding box kasar: 1 derajat lat ~ 111 km. 50 meter ~ 0.0005 derajat
        delta_deg = 0.0005
        candidates = db.query(Report).filter(
            Report.latitude.between(latitude - delta_deg, latitude + delta_deg),
            Report.longitude.between(longitude - delta_deg, longitude + delta_deg),
            Report.status.notin_(["Selesai", "Ditolak"])
        ).all()

        for candidate in candidates:
            dist = haversine_distance(latitude, longitude, candidate.latitude, candidate.longitude)
            if dist <= radius_meters:
                return candidate

        return None

    @classmethod
    def merge_or_create(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        confidence: float,
        image_path: str,
        radius_meters: float = settings.DEDUPLICATION_RADIUS_METERS
    ) -> Tuple[Optional[Report], bool]:
        """
        SRS FR-21: Jika laporan duplikat, backend menggabungkannya ke laporan yang ada
        dan menambah penghitung 'jumlah terlapor'.
        """
        duplicate = cls.find_duplicate_report(db, latitude, longitude, radius_meters)
        if duplicate:
            duplicate.jumlah_terlapor += 1
            # Perbarui gambar jika deteksi baru memiliki confidence lebih tinggi
            if confidence > duplicate.confidence:
                duplicate.confidence = confidence
                duplicate.gambar_path = image_path
            db.commit()
            db.refresh(duplicate)
            return duplicate, True

        return None, False

