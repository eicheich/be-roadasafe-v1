import os
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app, init_database_data
from app.core.config import settings
from app.core.database import Base, engine

client = TestClient(app)


def setup_module(module):
    # Inisialisasi basis data pengujian yang bersih
    Base.metadata.drop_all(bind=engine)
    init_database_data()


def test_root_and_health():
    res = client.get("/")
    assert res.status_code == 200
    assert "version" in res.json()

    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_auth_login_admin():
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@roadasafe.com",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["peran"] == "admin"


def test_auth_register_pelapor():
    res = client.post("/api/v1/auth/register", json={
        "nama": "Budi Pengemudi",
        "email": "budi@example.com",
        "password": "password123",
        "peran": "pelapor"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "budi@example.com"
    assert data["peran"] == "pelapor"


def test_device_registration():
    # Login as admin to get token
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@roadasafe.com",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/devices/register", json={
        "id": "device-pixel7-001",
        "model_perangkat": "Google Pixel 7",
        "versi_app": "1.0.0"
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == "device-pixel7-001"


def test_report_submission_and_urgency_calculation():
    # Buat dummy image
    image_bytes = b"fake image content for testing"
    files = {"gambar": ("test_pothole.jpg", io.BytesIO(image_bytes), "image/jpeg")}
    
    # 1. Test parameter normal: L=30, K=20, P=20, T=30 -> Low/Medium
    # Skor = 0.35*30 + 0.25*20 + 0.20*20 + 0.20*30 = 10.5 + 5 + 4 + 6 = 25.5 -> Low (0-33)
    data = {
        "device_id": "device-pixel7-001",
        "latitude": "-6.595038",
        "longitude": "106.816635",
        "akurasi_gps": "5.0",
        "confidence": "0.85",
        "nilai_L": "30.0",
        "nilai_K": "20.0",
        "nilai_P": "20.0",
        "nilai_T": "30.0",
        "versi_model": "yolov8n-pothole-v1.0"
    }
    
    res = client.post("/api/v1/reports/", data=data, files=files)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["skor"] == 25.5
    assert res_data["kategori"] == "Low"
    assert res_data["status"] == "Pending"
    assert res_data["jumlah_terlapor"] == 1


def test_report_safety_override():
    # Safety override: L >= 70, P >= 80 (tengah lajur), T >= 80 (arteri) -> High otomatis
    image_bytes = b"fake image content 2"
    files = {"gambar": ("test_high.jpg", io.BytesIO(image_bytes), "image/jpeg")}
    data = {
        "device_id": "device-pixel7-001",
        "latitude": "-6.650000",
        "longitude": "106.850000",
        "akurasi_gps": "8.0",
        "confidence": "0.92",
        "nilai_L": "80.0",
        "nilai_K": "30.0",
        "nilai_P": "100.0",
        "nilai_T": "100.0",
        "versi_model": "yolov8n-pothole-v1.0"
    }
    res = client.post("/api/v1/reports/", data=data, files=files)
    assert res.status_code == 201
    assert res.json()["kategori"] == "High"


def test_report_gps_accuracy_validation():
    # FR-13: Menolak laporan jika akurasi GPS > 20 meter
    image_bytes = b"fake image"
    files = {"gambar": ("bad_gps.jpg", io.BytesIO(image_bytes), "image/jpeg")}
    data = {
        "device_id": "device-pixel7-001",
        "latitude": "-6.600000",
        "longitude": "106.800000",
        "akurasi_gps": "35.0",  # Buruk > 20m
        "confidence": "0.85",
        "nilai_L": "30.0",
        "nilai_K": "20.0",
        "nilai_P": "20.0",
        "nilai_T": "30.0"
    }
    res = client.post("/api/v1/reports/", data=data, files=files)
    assert res.status_code == 422
    assert "Akurasi GPS" in res.json()["detail"]


def test_report_deduplication():
    # FR-16 & FR-21: Kirim laporan pada titik yang sangat dekat (< 15 meter)
    # Titik awal: -6.595038, 106.816635
    # Selisih sangat kecil: ~3 meter
    image_bytes = b"duplicate test image"
    files = {"gambar": ("dup.jpg", io.BytesIO(image_bytes), "image/jpeg")}
    data = {
        "device_id": "device-pixel7-002",
        "latitude": "-6.595045",
        "longitude": "106.816640",
        "akurasi_gps": "4.0",
        "confidence": "0.95",
        "nilai_L": "30.0",
        "nilai_K": "20.0",
        "nilai_P": "20.0",
        "nilai_T": "30.0"
    }
    res = client.post("/api/v1/reports/", data=data, files=files)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["is_duplicate"] is True
    assert res_data["jumlah_terlapor"] >= 2


def test_report_map_markers():
    res = client.get("/api/v1/reports/map")
    assert res.status_code == 200
    markers = res.json()
    assert len(markers) > 0
    for marker in markers:
        assert "color" in marker
        assert marker["color"] in ["#22c55e", "#eab308", "#ef4444", "#3b82f6"]


def test_admin_update_status_and_status_log():
    # Login admin
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@roadasafe.com",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ambil laporan pertama
    reports = client.get("/api/v1/reports/").json()
    report_id = reports[0]["id"]

    # Update status ke Terverifikasi (FR-25)
    patch_res = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "Terverifikasi", "catatan": "Telah diverifikasi via citra jalan"},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Terverifikasi"

    # Detail report harus memiliki status_logs (FR-27)
    detail_res = client.get(f"/api/v1/reports/{report_id}")
    assert detail_res.status_code == 200
    logs = detail_res.json()["status_logs"]
    assert len(logs) > 0
    assert any(log["status_baru"] == "Terverifikasi" for log in logs)


def test_export_csv():
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@roadasafe.com",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/reports/export/csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "ID,Device ID,Latitude,Longitude" in res.text


def test_recalculate_scores():
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@roadasafe.com",
        "password": "admin123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/reports/recalculate", headers=headers)
    assert res.status_code == 200
    assert res.json()["recalculated_count"] >= 1
