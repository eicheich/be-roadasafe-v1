import os
import uuid
import csv
import io
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.report import Report, ReportParameter
from app.models.status_log import StatusLog
from app.models.device import Device
from app.services.urgency_service import UrgencyService
from app.services.deduplication_service import DeduplicationService
from app.utils.geo import haversine_distance


class ReportService:
    @staticmethod
    def ensure_upload_dir() -> str:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        return settings.UPLOAD_DIR

    @classmethod
    async def save_image(cls, file: UploadFile) -> str:
        upload_dir = cls.ensure_upload_dir()
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        if not file_ext:
            file_ext = ".jpg"
        
        filename = f"{uuid.uuid4().hex}{file_ext}"
        content = await file.read()

        # Simpan ke disk lokal
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)
            
        relative_local_path = f"uploads/reports/{filename}"

        # Integrasi Supabase Storage jika SUPABASE_URL & KEY terkonfigurasi
        supabase_key = settings.effective_supabase_key
        if settings.SUPABASE_URL and supabase_key:
            try:
                from supabase import create_client
                client = create_client(settings.SUPABASE_URL, supabase_key)
                
                content_type = file.content_type or "image/jpeg"
                client.storage.from_(settings.SUPABASE_BUCKET).upload(
                    path=filename,
                    file=content,
                    file_options={"content-type": content_type}
                )
                public_url = client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(filename)
                return public_url
            except Exception:
                # Graceful fallback ke local file path
                return relative_local_path

        return relative_local_path

    @classmethod
    async def create_report(
        cls,
        db: Session,
        device_id: Optional[str],
        latitude: float,
        longitude: float,
        akurasi_gps: float,
        kecepatan: Optional[float],
        arah: Optional[float],
        waktu: Optional[datetime],
        confidence: float,
        nilai_L: float,
        nilai_K: float,
        nilai_P: float,
        nilai_T: float,
        versi_model: str,
        image_file: UploadFile,
        lokasi_jalan: Optional[str] = None,
        tipe_kerusakan: Optional[str] = "Lubang (Pothole)",
        estimasi_kedalaman_cm: Optional[float] = None
    ) -> Tuple[Report, bool]:
        """
        Membuat laporan baru atau menggabungkannya ke laporan yang ada jika duplikat (FR-16, FR-21).
        Juga memvalidasi batas data (FR-19) dan akurasi GPS (FR-13).
        """
        # Validasi FR-13: Tolak jika akurasi GPS lebih buruk dari ambang batas (20 meter)
        if akurasi_gps > settings.MAX_GPS_ACCURACY_METERS:
            raise HTTPException(
                status_code=422,
                detail=f"Akurasi GPS ({akurasi_gps} m) lebih buruk dari ambang batas maksimum ({settings.MAX_GPS_ACCURACY_METERS} m). Laporan ditolak demi integritas data lokasi."
            )

        # Validasi rentang koordinat (FR-19)
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise HTTPException(
                status_code=422,
                detail="Koordinat GPS tidak valid (latitude: -90 s/d 90, longitude: -180 s/d 180)."
            )

        # Validasi rentang parameter (FR-19)
        for name, val in [("L", nilai_L), ("K", nilai_K), ("P", nilai_P), ("T", nilai_T)]:
            if not (0.0 <= val <= 100.0):
                raise HTTPException(
                    status_code=422,
                    detail=f"Nilai parameter {name} ({val}) berada di luar rentang valid 0-100."
                )

        if not (0.0 <= confidence <= 1.0):
            raise HTTPException(
                status_code=422,
                detail=f"Confidence ({confidence}) harus berada pada rentang 0.0 - 1.0."
            )

        # Pastikan device tercatat jika device_id diberikan
        if device_id:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                device = Device(id=device_id, is_active=True)
                db.add(device)
                db.commit()

        # Simpan file gambar
        saved_image_path = await cls.save_image(image_file)

        # Cek deduplikasi server-side (FR-16, FR-21)
        duplicate, is_dup = DeduplicationService.merge_or_create(
            db=db,
            latitude=latitude,
            longitude=longitude,
            confidence=confidence,
            image_path=saved_image_path,
            radius_meters=settings.DEDUPLICATION_RADIUS_METERS
        )
        if is_dup and duplicate:
            return duplicate, True

        # Hitung skor urgensi dan kategori sesuai rumus Bagian 5
        config = UrgencyService.get_active_config(db)
        skor, kategori = UrgencyService.calculate_score(
            nilai_L, nilai_K, nilai_P, nilai_T, config
        )

        report_time = waktu if waktu else datetime.now(timezone.utc)
        depth_est = estimasi_kedalaman_cm if estimasi_kedalaman_cm is not None else round(nilai_K * 0.12, 1)

        new_report = Report(
            device_id=device_id,
            latitude=latitude,
            longitude=longitude,
            akurasi_gps=akurasi_gps,
            kecepatan=kecepatan,
            arah=arah,
            waktu=report_time,
            lokasi_jalan=lokasi_jalan or "Jl. Pajajaran, Bogor",
            tipe_kerusakan=tipe_kerusakan or "Lubang (Pothole)",
            estimasi_kedalaman_cm=depth_est,
            gambar_path=saved_image_path,
            confidence=confidence,
            skor=skor,
            kategori=kategori,
            status="Pending",
            jumlah_terlapor=1,
            versi_model=versi_model or config.versi_model_aktif
        )
        db.add(new_report)
        db.flush()

        # Format kode laporan sesuai format UI: #RS-2026-0892
        new_report.kode_laporan = f"#RS-{report_time.year}-{new_report.id:04d}"

        param = ReportParameter(
            report_id=new_report.id,
            nilai_L=nilai_L,
            nilai_K=nilai_K,
            nilai_P=nilai_P,
            nilai_T=nilai_T
        )
        db.add(param)

        initial_log = StatusLog(
            report_id=new_report.id,
            status_lama="None",
            status_baru="Pending",
            diubah_oleh="Sistem (Laporan Masuk)",
            catatan="Laporan otomatis diterima dari perangkat",
            waktu=report_time
        )
        db.add(initial_log)

        db.commit()
        db.refresh(new_report)
        return new_report, False

        param = ReportParameter(
            report_id=new_report.id,
            nilai_L=nilai_L,
            nilai_K=nilai_K,
            nilai_P=nilai_P,
            nilai_T=nilai_T
        )
        db.add(param)

        initial_log = StatusLog(
            report_id=new_report.id,
            status_lama="None",
            status_baru="Pending",
            diubah_oleh="Sistem (Laporan Masuk)",
            catatan="Laporan otomatis diterima dari perangkat",
            waktu=report_time
        )
        db.add(initial_log)

        db.commit()
        db.refresh(new_report)
        return new_report, False

    @staticmethod
    def update_status(
        db: Session,
        report_id: int,
        status_baru: str,
        diubah_oleh: str,
        catatan: Optional[str] = None
    ) -> Report:
        """
        SRS FR-25 & FR-27: Mengubah status laporan dan mencatat log audit ke StatusLog.
        Status valid: Pending, Terverifikasi, Dalam Penanganan, Selesai, Ditolak.
        """
        valid_statuses = ["Pending", "Terverifikasi", "Dalam Penanganan", "Selesai", "Ditolak"]
        if status_baru not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status '{status_baru}' tidak valid. Pilihan: {', '.join(valid_statuses)}"
            )

        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Laporan dengan ID {report_id} tidak ditemukan."
            )

        status_lama = report.status
        report.status = status_baru

        log = StatusLog(
            report_id=report.id,
            status_lama=status_lama,
            status_baru=status_baru,
            diubah_oleh=diubah_oleh,
            catatan=catatan,
            waktu=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_reports(
        db: Session,
        kategori: Optional[str] = None,
        status_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        device_id: Optional[str] = None,
        search: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Report]:
        query = db.query(Report)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Report.lokasi_jalan.ilike(search_pattern)) |
                (Report.kode_laporan.ilike(search_pattern))
            )

        if kategori:
            kat_lower = kategori.lower()
            if kat_lower in ["tinggi", "high"]:
                query = query.filter(Report.kategori.in_(["High", "Tinggi"]))
            elif kat_lower in ["sedang", "medium"]:
                query = query.filter(Report.kategori.in_(["Medium", "Sedang"]))
            elif kat_lower in ["rendah", "low"]:
                query = query.filter(Report.kategori.in_(["Low", "Rendah"]))
            else:
                query = query.filter(Report.kategori == kategori)

        if status_filter:
            if status_filter.lower() != "semua":
                query = query.filter(Report.status.ilike(status_filter))
        if start_date:
            query = query.filter(Report.waktu >= start_date)
        if end_date:
            query = query.filter(Report.waktu <= end_date)
        if device_id:
            query = query.filter(Report.device_id == device_id)

        # Filtering radius jika koordinat tengah dan radius diberikan
        if lat is not None and lon is not None and radius_km is not None:
            # 1 km ~ 0.009 derajat lat
            delta_deg = (radius_km / 111.0)
            query = query.filter(
                Report.latitude.between(lat - delta_deg, lat + delta_deg),
                Report.longitude.between(lon - delta_deg, lon + delta_deg)
            )

        reports = query.order_by(Report.waktu.desc()).offset(skip).limit(limit).all()

        # Presisi filtering radius dengan haversine jika radius_km ditentukan
        if lat is not None and lon is not None and radius_km is not None:
            max_meters = radius_km * 1000.0
            filtered = [
                r for r in reports
                if haversine_distance(lat, lon, r.latitude, r.longitude) <= max_meters
            ]
            return filtered

        return reports

    @staticmethod
    def get_map_markers(db: Session) -> List[dict]:
        """
        SRS FR-24: Penanda peta berwarna sesuai urgensi (hijau/kuning/merah).
        """
        reports = db.query(Report).filter(Report.status != "Ditolak").all()
        markers = []
        for r in reports:
            # Hijau (Low/Rendah), Kuning (Medium/Sedang), Merah (High/Tinggi)
            color_map = {
                "Low": "#22c55e",
                "Rendah": "#22c55e",
                "Medium": "#eab308",
                "Sedang": "#eab308",
                "High": "#ef4444",
                "Tinggi": "#ef4444"
            }
            markers.append({
                "id": r.id,
                "kode_laporan": r.kode_laporan or f"#RS-2026-{r.id:04d}",
                "lokasi_jalan": r.lokasi_jalan,
                "tipe_kerusakan": r.tipe_kerusakan,
                "estimasi_kedalaman_cm": r.estimasi_kedalaman_cm,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "skor": r.skor,
                "kategori": r.kategori,
                "status": r.status,
                "color": color_map.get(r.kategori, "#3b82f6"),
                "jumlah_terlapor": r.jumlah_terlapor,
                "waktu": r.waktu
            })
        return markers

    @staticmethod
    def get_summary(db: Session) -> dict:
        """
        Menyajikan metrik KPI untuk 4 kartu ringkasan di dashboard UI-W01:
        1. Total Laporan Terdata
        2. Menunggu Verifikasi (Pending)
        3. Terverifikasi & Ditangani (Terverifikasi + Dalam Penanganan)
        4. Selesai Ditambal (Selesai)
        """
        total = db.query(Report).count()
        menunggu = db.query(Report).filter(Report.status == "Pending").count()
        terverifikasi = db.query(Report).filter(Report.status.in_(["Terverifikasi", "Dalam Penanganan"])).count()
        selesai = db.query(Report).filter(Report.status == "Selesai").count()
        ditolak = db.query(Report).filter(Report.status == "Ditolak").count()
        
        tinggi = db.query(Report).filter(Report.kategori.in_(["High", "Tinggi"])).count()
        sedang = db.query(Report).filter(Report.kategori.in_(["Medium", "Sedang"])).count()
        rendah = db.query(Report).filter(Report.kategori.in_(["Low", "Rendah"])).count()

        return {
            "total_laporan": total,
            "menunggu_verifikasi": menunggu,
            "terverifikasi_ditangani": terverifikasi,
            "selesai_ditambal": selesai,
            "ditolak": ditolak,
            "urgensi": {
                "tinggi": tinggi,
                "sedang": sedang,
                "rendah": rendah
            }
        }

    @classmethod
    def export_csv(cls, db: Session, reports: List[Report]) -> str:
        """
        SRS FR-26: Admin dapat mengekspor laporan (CSV).
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Device ID", "Latitude", "Longitude", "Akurasi GPS (m)",
            "Kecepatan", "Arah", "Waktu", "Confidence", "Nilai L", "Nilai K",
            "Nilai P", "Nilai T", "Skor Urgensi", "Kategori", "Status",
            "Jumlah Terlapor", "Versi Model", "Gambar Path"
        ])
        for r in reports:
            writer.writerow([
                r.id,
                r.device_id or "",
                r.latitude,
                r.longitude,
                r.akurasi_gps,
                r.kecepatan or "",
                r.arah or "",
                r.waktu.isoformat() if r.waktu else "",
                r.confidence,
                r.parameter.nilai_L if r.parameter else "",
                r.parameter.nilai_K if r.parameter else "",
                r.parameter.nilai_P if r.parameter else "",
                r.parameter.nilai_T if r.parameter else "",
                r.skor,
                r.kategori,
                r.status,
                r.jumlah_terlapor,
                r.versi_model,
                r.gambar_path
            ])
        return output.getvalue()
