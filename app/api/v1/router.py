from fastapi import APIRouter
from app.api.v1.endpoints import auth, devices, reports, configs, roads, health

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Autentikasi & Pengguna"])
api_v1_router.include_router(devices.router, prefix="/devices", tags=["Perangkat Mobile"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["Laporan Kerusakan"])
api_v1_router.include_router(configs.router, prefix="/config", tags=["Konfigurasi Bobot & Ambang"])
api_v1_router.include_router(roads.router, prefix="/roads", tags=["Kelas Jalan & Kepadatan"])
api_v1_router.include_router(health.router, prefix="/health", tags=["Health & Database Check"])

