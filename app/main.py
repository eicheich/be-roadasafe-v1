import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal, get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.config import SystemConfig
from app.models.road_class import RoadClass
from app.api.v1.router import api_v1_router
from app.services.report_service import ReportService


def init_database_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Pastikan default admin ada
        admin = db.query(User).filter(User.email == "admin@roadasafe.com").first()
        if not admin:
            admin = User(
                nama="Administrator RoadSafe",
                email="admin@roadasafe.com",
                password_hash=hash_password("admin123"),
                peran="admin"
            )
            db.add(admin)

        # Admin Verifikator sesuai mockup UI-W00
        verifikator = db.query(User).filter(User.email == "verifikator@pupr.go.id").first()
        if not verifikator:
            verifikator = User(
                nama="Budi Santoso (Verifikator - Bina Marga)",
                email="verifikator@pupr.go.id",
                password_hash=hash_password("secretPassword123"),
                peran="admin"
            )
            db.add(verifikator)

        # 2. Pastikan SystemConfig awal ada (SRS Bagian 5)
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

        # 3. Seed kelas jalan default (SRS Bagian 5.2)
        if db.query(RoadClass).count() == 0:
            roads = [
                RoadClass(nama_jalan="Jalan Pajajaran", kelas="arteri", bobot_kepadatan=100.0),
                RoadClass(nama_jalan="Jalan Surya Kencana", kelas="kolektor", bobot_kepadatan=60.0),
                RoadClass(nama_jalan="Jalan Babakan Raya", kelas="lokal", bobot_kepadatan=30.0),
            ]
            db.add_all(roads)

        # 4. Seed data sampel sesuai tampilan mockup UI-W01 & UI-W02 jika database masih kosong
        from app.models.report import Report, ReportParameter
        from app.models.status_log import StatusLog
        from datetime import datetime, timezone

        if db.query(Report).count() == 0:
            sample_data = [
                {
                    "kode": "#RS-2026-0892",
                    "jalan": "Jl. Pajajaran No. 45, Bogor Tengah",
                    "lat": -6.597147, "lon": 106.806038, "akurasi": 3.8, "kecepatan": 34.5, "arah": 182.0,
                    "skor": 78.4, "kategori": "High", "status": "Pending", "jumlah": 4, "kedalaman": 8.5,
                    "tipe": "Lubang Kritis (Pothole)", "L": 80.0, "K": 65.0, "P": 100.0, "T": 60.0, "conf": 0.84
                },
                {
                    "kode": "#RS-2026-0891",
                    "jalan": "Jl. Raya Tajur KM 4.2",
                    "lat": -6.621450, "lon": 106.828450, "akurasi": 4.1, "kecepatan": 42.0, "arah": 140.0,
                    "skor": 54.2, "kategori": "Medium", "status": "Terverifikasi", "jumlah": 2, "kedalaman": 5.0,
                    "tipe": "Retak Buaya (Alligator)", "L": 50.0, "K": 45.0, "P": 60.0, "T": 60.0, "conf": 0.79
                },
                {
                    "kode": "#RS-2026-0890",
                    "jalan": "Jl. Surya Kencana No. 12",
                    "lat": -6.605120, "lon": 106.801230, "akurasi": 5.0, "kecepatan": 28.0, "arah": 95.0,
                    "skor": 41.5, "kategori": "Medium", "status": "Pending", "jumlah": 1, "kedalaman": 4.2,
                    "tipe": "Amblas / Depresi", "L": 40.0, "K": 35.0, "P": 60.0, "T": 30.0, "conf": 0.81
                },
                {
                    "kode": "#RS-2026-0889",
                    "jalan": "Jl. Juanda Depan Museum Zoologi",
                    "lat": -6.599810, "lon": 106.795400, "akurasi": 3.5, "kecepatan": 30.0, "arah": 210.0,
                    "skor": 82.1, "kategori": "High", "status": "Dalam Penanganan", "jumlah": 2, "kedalaman": 9.2,
                    "tipe": "Lubang Kritis (Pothole)", "L": 85.0, "K": 75.0, "P": 100.0, "T": 60.0, "conf": 0.88
                },
                {
                    "kode": "#RS-2026-0888",
                    "jalan": "Jl. Pemuda No. 8",
                    "lat": -6.582100, "lon": 106.796300, "akurasi": 4.5, "kecepatan": 35.0, "arah": 15.0,
                    "skor": 32.0, "kategori": "Low", "status": "Selesai", "jumlah": 1, "kedalaman": 2.5,
                    "tipe": "Alur Roda (Rutting)", "L": 30.0, "K": 25.0, "P": 30.0, "T": 30.0, "conf": 0.76
                }
            ]

            now = datetime.now(timezone.utc)
            for item in sample_data:
                rep = Report(
                    kode_laporan=item["kode"],
                    lokasi_jalan=item["jalan"],
                    latitude=item["lat"],
                    longitude=item["lon"],
                    akurasi_gps=item["akurasi"],
                    kecepatan=item["kecepatan"],
                    arah=item["arah"],
                    waktu=now,
                    tipe_kerusakan=item["tipe"],
                    estimasi_kedalaman_cm=item["kedalaman"],
                    gambar_path="uploads/reports/sample_pothole.jpg",
                    confidence=item["conf"],
                    skor=item["skor"],
                    kategori=item["kategori"],
                    status=item["status"],
                    jumlah_terlapor=item["jumlah"],
                    versi_model="yolov8n-pothole-v1.0"
                )
                db.add(rep)
                db.flush()

                param = ReportParameter(
                    report_id=rep.id,
                    nilai_L=item["L"],
                    nilai_K=item["K"],
                    nilai_P=item["P"],
                    nilai_T=item["T"]
                )
                db.add(param)

                log = StatusLog(
                    report_id=rep.id,
                    status_lama="None",
                    status_baru=item["status"],
                    diubah_oleh="Sistem Inisialisasi Mockup",
                    catatan=f"Data sinkronisasi inspeksi {item['jalan']}",
                    waktu=now
                )
                db.add(log)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Siapkan direktori penyimpanan & data awal
    ReportService.ensure_upload_dir()
    init_database_data()
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    Backend API untuk Sistem Deteksi dan Klasifikasi Tingkat Urgensi Jalan Berlubang Secara Real-Time
    Berbasis YOLOv8 dengan Pelaporan Otomatis Terintegrasi GPS pada Aplikasi Mobile.
    
    Fitur Utama sesuai SRS:
    - Autentikasi JWT & Manajemen Perangkat Mobile (FR-18, Section 7)
    - Pelaporan Berlokasi GPS dengan Upload Foto Bukti (FR-12, FR-14, FR-20)
    - Validasi Data & Penolakan Akurasi GPS Buruk > 20m (FR-13, FR-19)
    - Deduplikasi Laporan Spasial Server-side (FR-16, FR-21)
    - Model Penilaian Urgensi 4 Parameter (L, K, P, T) & Override Keselamatan (Section 5)
    - Manajemen Status Verifikasi Human-in-the-Loop & Audit Log (FR-22, FR-25, FR-27)
    - Penyajian Titik Peta Warna Urgensi (FR-24) & Ekspor CSV (FR-26)
    - Konfigurasi Bobot Dinamis & Hitung Ulang Skor (FR-23)
    """,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount direktori uploads agar file foto bukti dapat diakses langsung oleh dashboard/klien
ReportService.ensure_upload_dir()
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include Router API v1
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/health/db", tags=["Health"])
def db_health_check(db = Depends(get_db)):
    from app.api.v1.endpoints.health import check_database_connection
    return check_database_connection(db=db)
