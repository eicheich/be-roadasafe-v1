from typing import Tuple
from sqlalchemy.orm import Session
from app.models.config import SystemConfig
from app.models.report import Report


class UrgencyService:
    @staticmethod
    def get_active_config(db: Session) -> SystemConfig:
        config = db.query(SystemConfig).first()
        if not config:
            config = SystemConfig(
                bobot_L=0.35,
                bobot_K=0.25,
                bobot_P=0.20,
                bobot_T=0.20,
                ambang_low=33.0,
                ambang_medium=66.0,
                versi_model_aktif="yolov8n-pothole-v1.0"
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    @classmethod
    def calculate_score(
        cls,
        nilai_L: float,
        nilai_K: float,
        nilai_P: float,
        nilai_T: float,
        config: SystemConfig
    ) -> Tuple[float, str]:
        """
        Menghitung skor urgensi berdasarkan formula pada SRS Bagian 5:
        Skor = bobot_L * L + bobot_K * K + bobot_P * P + bobot_T * T
        
        Kategori:
        - Low: 0 - 33
        - Medium: 34 - 66
        - High: 67 - 100
        
        Aturan Tambahan (SRS 5.4):
        Override keselamatan: lubang besar di tengah lajur jalan arteri otomatis High,
        terlepas dari skor total.
        """
        # Safety override rule: lubang besar (L >= 70) di tengah lajur (P >= 80) jalan arteri (T >= 80)
        if nilai_L >= 70.0 and nilai_P >= 80.0 and nilai_T >= 80.0:
            skor = (
                (config.bobot_L * nilai_L) +
                (config.bobot_K * nilai_K) +
                (config.bobot_P * nilai_P) +
                (config.bobot_T * nilai_T)
            )
            skor = round(min(max(skor, 0.0), 100.0), 2)
            return skor, "High"

        # Standard calculation
        skor = (
            (config.bobot_L * nilai_L) +
            (config.bobot_K * nilai_K) +
            (config.bobot_P * nilai_P) +
            (config.bobot_T * nilai_T)
        )
        skor = round(min(max(skor, 0.0), 100.0), 2)

        if skor <= config.ambang_low:
            kategori = "Low"
        elif skor <= config.ambang_medium:
            kategori = "Medium"
        else:
            kategori = "High"

        return skor, kategori

    @classmethod
    def recalculate_all_reports(cls, db: Session) -> int:
        """
        SRS FR-23: Backend dapat mengulang perhitungan skor jika bobot/ambang batas diubah.
        """
        config = cls.get_active_config(db)
        reports = db.query(Report).all()
        count = 0
        for report in reports:
            if report.parameter:
                new_score, new_category = cls.calculate_score(
                    report.parameter.nilai_L,
                    report.parameter.nilai_K,
                    report.parameter.nilai_P,
                    report.parameter.nilai_T,
                    config
                )
                report.skor = new_score
                report.kategori = new_category
                count += 1
        db.commit()
        return count

