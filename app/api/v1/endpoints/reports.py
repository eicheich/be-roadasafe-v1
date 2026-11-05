from datetime import datetime
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
    Response,
    status
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import verify_device_rate_limit
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    ReportResponse,
    ReportStatusUpdate,
    ReportMapItem,
    ReportSummaryResponse,
    RecalculateResponse
)
from app.services.report_service import ReportService
from app.services.urgency_service import UrgencyService
from app.api.deps import get_current_user, get_current_admin

router = APIRouter()


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(
    gambar: UploadFile = File(..., description="Foto bukti jalan berlubang"),
    device_id: Optional[str] = Form(None, description="ID unik perangkat mobile"),
    latitude: float = Form(..., description="Koordinat lintang"),
    longitude: float = Form(..., description="Koordinat bujur"),
    akurasi_gps: float = Form(..., description="Akurasi sinyal GPS dalam meter"),
    kecepatan: Optional[float] = Form(None, description="Kecepatan kendaraan saat deteksi"),
    arah: Optional[float] = Form(None, description="Arah pergerakan kendaraan"),
    confidence: float = Form(..., description="Nilai kepercayaan model YOLOv8 (0.0 - 1.0)"),
    nilai_L: float = Form(..., description="Luas area kerusakan terbobot (0 - 100)"),
    nilai_K: float = Form(..., description="Rasio kedalaman/bentuk (0 - 100)"),
    nilai_P: float = Form(..., description="Posisi pada jalur (0 - 100)"),
    nilai_T: float = Form(..., description="Kepadatan lalu lintas jalan (0 - 100)"),
    lokasi_jalan: Optional[str] = Form(None, description="Nama ruas jalan atau alamat lokasi"),
    tipe_kerusakan: Optional[str] = Form("Lubang (Pothole)", description="Jenis kerusakan"),
    estimasi_kedalaman_cm: Optional[float] = Form(None, description="Estimasi kedalaman dalam cm"),
    versi_model: Optional[str] = Form("yolov8n-pothole-v1.0", description="Versi model YOLOv8"),
    waktu: Optional[datetime] = Form(None, description="Waktu kejadian (default saat ini)"),
    db: Session = Depends(get_db)
):
    """
    SRS FR-12 s/d FR-21: Menerima laporan otomatis dari aplikasi mobile:
    - Verifikasi rate limit per perangkat (FR-17)
    - Validasi format data & rentang nilai (FR-19)
    - Penolakan jika akurasi GPS > 20 meter (FR-13)
    - Perhitungan skor & kategori urgensi (Bagian 5)
    - Deduplikasi spasial 10-15 meter (FR-16, FR-21)
    - Penyimpanan file gambar & entitas database (FR-20)
    """
    # Rate limit check per device
    effective_device = device_id or "anonymous_device"
    verify_device_rate_limit(effective_device)

    report, is_duplicate = await ReportService.create_report(
        db=db,
        device_id=device_id,
        latitude=latitude,
        longitude=longitude,
        akurasi_gps=akurasi_gps,
        kecepatan=kecepatan,
        arah=arah,
        waktu=waktu,
        confidence=confidence,
        nilai_L=nilai_L,
        nilai_K=nilai_K,
        nilai_P=nilai_P,
        nilai_T=nilai_T,
        versi_model=versi_model or "yolov8n-pothole-v1.0",
        image_file=gambar,
        lokasi_jalan=lokasi_jalan,
        tipe_kerusakan=tipe_kerusakan,
        estimasi_kedalaman_cm=estimasi_kedalaman_cm
    )

    report_response = ReportResponse.model_validate(report)
    report_response.is_duplicate = is_duplicate
    return report_response


@router.get("/summary", response_model=ReportSummaryResponse)
def get_reports_summary(db: Session = Depends(get_db)):
    """
    Menyajikan 4 kartu metrik KPI utama sesuai dashboard UI-W01:
    - Total Laporan Terdata
    - Menunggu Verifikasi
    - Terverifikasi & Ditangani
    - Selesai Ditambal
    """
    return ReportService.get_summary(db)


@router.get("/", response_model=List[ReportResponse])
def get_reports(
    kategori: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    device_id: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    SRS FR-22: Daftar laporan dengan berbagai filter (kategori, status, tanggal, area, pencarian nama jalan).
    """
    return ReportService.get_reports(
        db=db,
        kategori=kategori,
        status_filter=status_filter,
        search=search,
        start_date=start_date,
        end_date=end_date,
        device_id=device_id,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        skip=skip,
        limit=limit
    )


@router.get("/map", response_model=List[ReportMapItem])
def get_map_reports(db: Session = Depends(get_db)):
    """
    SRS FR-24 & 3.1: Mengambil titik-titik laporan untuk peta dengan warna sesuai tingkat urgensi:
    - Hijau = Low
    - Kuning = Medium
    - Merah = High
    """
    return ReportService.get_map_markers(db)


@router.get("/export/csv")
def export_reports_csv(
    kategori: Optional[str] = None,
    status_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    SRS FR-26: Admin mengekspor laporan dalam bentuk CSV.
    """
    reports = ReportService.get_reports(
        db=db,
        kategori=kategori,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        limit=10000
    )
    csv_data = ReportService.export_csv(db, reports)
    filename = f"laporan_jalan_berlubang_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{id}", response_model=ReportResponse)
def get_report_detail(id: int, db: Session = Depends(get_db)):
    """
    SRS FR-22: Detail lengkap sebuah laporan beserta parameter uji dan riwayat status (StatusLog).
    """
    report = db.query(Report).filter(Report.id == id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laporan dengan ID {id} tidak ditemukan"
        )
    return report


@router.patch("/{id}/status", response_model=ReportResponse)
def update_report_status(
    id: int,
    status_data: ReportStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    SRS FR-25 & FR-27: Admin mengubah status verifikasi laporan:
    Pending -> Terverifikasi -> Dalam Penanganan -> Selesai, atau Ditolak (false positive).
    Perubahan status dicatat di StatusLog untuk audit dan retraining model.
    """
    updated_report = ReportService.update_status(
        db=db,
        report_id=id,
        status_baru=status_data.status,
        diubah_oleh=f"{admin.nama} ({admin.email})",
        catatan=status_data.catatan
    )
    return updated_report


@router.post("/recalculate", response_model=RecalculateResponse)
def recalculate_scores(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    SRS FR-23: Backend mengulang perhitungan skor & kategori jika bobot/ambang batas diubah.
    """
    count = UrgencyService.recalculate_all_reports(db)
    return {
        "recalculated_count": count,
        "message": f"Berhasil menghitung ulang skor dan kategori untuk {count} laporan berdasarkan bobot konfigurasi terkini."
    }

