# RoadSafe Backend API 🚦🛣️

Implementasi Backend REST API untuk **Sistem Deteksi dan Klasifikasi Tingkat Urgensi Jalan Berlubang Berbasis YOLOv8 dengan Pelaporan Otomatis Terintegrasi GPS pada Aplikasi Mobile**, mengacu secara presisi pada dokumen spesifikasi **SRS (Software Requirements Specification)**.

---

## 📁 Folder Management & Struktur Arsitektur

Proyek diorganisasikan secara modular mengikuti pola Clean Architecture untuk FastAPI:

```text
be-roadasafe-v1/
├── app/
│   ├── api/                      # Routing & Controller layer
│   │   ├── deps.py               # Dependency injection (Auth Bearer & Admin guard)
│   │   ├── router.py             # Router aggregator
│   │   └── v1/
│   │       ├── router.py         # API v1 central router
│   │       └── endpoints/
│   │           ├── auth.py       # FR-18: Autentikasi JWT & User profile
│   │           ├── devices.py    # FR-14, Sec 7: Registrasi & verifikasi perangkat mobile
│   │           ├── reports.py    # FR-12 s/d FR-27: Upload foto, filter, peta, CSV, status
│   │           ├── configs.py    # UC-04, FR-23: Bobot L, K, P, T & ambang kategori
│   │           └── roads.py      # Sec 5.2, Sec 7: Lookup kelas jalan (arteri, kolektor, lokal)
│   ├── core/                     # Core configs & infrastructure
│   │   ├── config.py             # Settings (Pydantic Settings & env configuration)
│   │   ├── database.py           # SQLAlchemy engine & session management
│   │   ├── security.py           # Bcrypt hashing & JWT token encoding/decoding
│   │   └── rate_limit.py         # FR-17: Sliding-window rate limiter per device_id
│   ├── models/                   # SQLAlchemy ORM Database Models (SRS Bagian 7)
│   │   ├── user.py               # Tabel `users` (id, nama, email, peran, password_hash)
│   │   ├── device.py             # Tabel `devices` (id, user_id, model, versi_app)
│   │   ├── report.py             # Tabel `reports` & `report_parameters`
│   │   ├── status_log.py         # Tabel `status_logs` (riwayat audit human-in-the-loop)
│   │   ├── config.py             # Tabel `system_configs` (bobot & ambang)
│   │   └── road_class.py         # Tabel `road_classes` (nama jalan, kelas, bobot kepadatan)
│   ├── schemas/                  # Pydantic v2 DTO / Validation Schemas
│   │   ├── auth.py               # Request/Response registrasi & login
│   │   ├── device.py             # Schema registrasi perangkat
│   │   ├── config.py             # Schema update & retrieve konfigurasi bobot
│   │   ├── road_class.py         # Schema kelas jalan
│   │   └── report.py             # Schema laporan, peta, parameter, status update
│   ├── services/                 # Business Logic Layer
│   │   ├── urgency_service.py    # Perhitungan Skor Urgensi (SRS Bagian 5) & Override High
│   │   ├── deduplication_service.py # FR-16, FR-21: Deduplikasi spasial (radius 10-15m)
│   │   └── report_service.py     # Penyimpanan foto, filter kueri, ekspor CSV, status log
│   ├── utils/                    # Utility Helpers
│   │   └── geo.py                # Formula jarak Haversine (meter)
│   └── main.py                   # Inisialisasi FastAPI, CORS, static files, data seeding
├── tests/                        # Automated Test Suite (Pytest)
│   └── test_api.py               # 12 skenario uji menyeluruh seluruh alur SRS
├── uploads/                      # Penyimpanan lokal foto bukti jalan berlubang
│   └── reports/
├── .env.example                  # Template variabel lingkungan
├── requirements.txt              # Daftar dependensi Python
├── run.py                        # Entrypoint server (python run.py)
└── README.md                     # Dokumentasi teknis
```

---

## 🎯 Pemetaan Kebutuhan SRS

| ID SRS | Kebutuhan | Implementasi di Backend |
|---|---|---|
| **FR-12 & FR-14** | Pelaporan otomatis berlokasi (GPS, arah, kecepatan, parameter, confidence, gambar, device_id) | `POST /api/v1/reports/` (multipart/form-data) |
| **FR-13** | Penolakan/penandaan jika akurasi GPS > 20 meter | Ditolak dengan kode HTTP 422 bila `akurasi_gps > 20.0` |
| **FR-16 & FR-21** | Deduplikasi sisi server (radius 10-15 meter) & penambahan `jumlah_terlapor` | `DeduplicationService.merge_or_create()` via Haversine distance |
| **FR-17** | Rate limit per perangkat mobile | `DeviceRateLimiter` (sliding-window per `device_id`, default 60 req/min) |
| **FR-18** | Autentikasi permintaan menggunakan token | JWT Bearer token authentication (`/api/v1/auth/login`) |
| **FR-19** | Validasi format dan rentang data | Pydantic & service checks: parameter L, K, P, T (0-100), confidence (0-1), koordinat valid |
| **FR-20** | Penyimpanan file gambar & titik lokasi | Foto disimpan di `uploads/reports/` dan disajikan via `/uploads/` |
| **FR-22** | Endpoint daftar, detail, filter (kategori, status, tanggal, area radius) | `GET /api/v1/reports/` & `GET /api/v1/reports/{id}` |
| **FR-23** | Hitung ulang skor jika bobot/ambang batas diubah | `POST /api/v1/reports/recalculate` & `PUT /api/v1/config/` |
| **FR-24** | Data tampilan peta dengan kode warna urgensi | `GET /api/v1/reports/map` (Hijau = Low, Kuning = Medium, Merah = High) |
| **FR-25** | Perubahan status verifikasi admin (Pending → Terverifikasi → Dalam Penanganan → Selesai / Ditolak) | `PATCH /api/v1/reports/{id}/status` |
| **FR-26** | Ekspor laporan ke CSV | `GET /api/v1/reports/export/csv` |
| **FR-27** | Pencatatan riwayat keputusan status (Audit Log / StatusLog) | Tabel `status_logs` mencatat status lama, baru, waktu, catatan & petugas |

---

## 🧮 Model Penilaian Urgensi (SRS Bagian 5)

Formula dasar:
$$\text{Skor} = 0.35 \times L + 0.25 \times K + 0.20 \times P + 0.20 \times T$$

- **L**: Luas Area Kerusakan (0–100)
- **K**: Rasio Kedalaman / Bentuk (0–100)
- **P**: Posisi pada Jalur (Tengah = 100, Tengah-sisi = 60, Tepi = 30, Bahu = 10)
- **T**: Kepadatan Lalu Lintas (Arteri = 100, Kolektor = 60, Lokal = 30)

**Ambang Kategori:**
- **Low**: $0 - 33$ (Pemantauan)
- **Medium**: $34 - 66$ (Dijadwalkan perbaikan)
- **High**: $67 - 100$ (Prioritas perbaikan)

**Aturan Override Keselamatan (SRS 5.4):**
Lubang besar ($L \ge 70$) di tengah lajur ($P \ge 80$) pada jalan arteri ($T \ge 80$) otomatis berkategori **High**, terlepas dari total perhitungannya.

---

## 🚀 Panduan Menjalankan

### 1. Instalasi Dependensi
```bash
pip install -r requirements.txt
```

### 2. Konfigurasi Lingkungan
Salin `.env.example` ke `.env`:
```bash
cp .env.example .env
```
Secara default menggunakan database SQLite (`sqlite:///./roadasafe.db`) sehingga dapat langsung dijalankan tanpa setup database eksternal. Untuk PostgreSQL + PostGIS, cukup ubah `DATABASE_URL` di file `.env`.

### 3. Menjalankan Server
```bash
python run.py
```
atau menggunakan uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Akses dokumentasi interaktif Swagger UI di:
👉 **http://localhost:8000/docs**

---

## 👤 Akun Default & Kredensial

Saat aplikasi pertama kali dijalankan, sistem secara otomatis menginisialisasi:
- **Email Admin:** `admin@roadasafe.com`
- **Kata Sandi:** `admin123`
- **Peran:** `admin`

---

## 🧪 Menjalankan Pengujian (Automated Tests)

Semua skenario pengujian fungsional SRS diuji menggunakan Pytest:
```bash
python -m pytest tests/test_api.py -v
```
Hasil pengujian: **12 passed**.

