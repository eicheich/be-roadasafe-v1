import time
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/db")
def check_database_connection(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Endpoint untuk mengecek koneksi database (SQLAlchemy) dan layanan Supabase.
    """
    # 1. Cek Koneksi Database Utama (SQLAlchemy - SQLite / PostgreSQL)
    db_result = {}
    db_start = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency = round((time.time() - db_start) * 1000, 2)
        
        # Sembunyikan kredensial password dari URL jika PostgreSQL
        masked_url = settings.DATABASE_URL
        if "@" in masked_url:
            prefix, rest = masked_url.split("://", 1)
            auth_part, host_part = rest.split("@", 1)
            user = auth_part.split(":")[0] if ":" in auth_part else auth_part
            masked_url = f"{prefix}://{user}:***@{host_part}"

        db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
        db_result = {
            "status": "connected",
            "type": db_type,
            "database_url": masked_url,
            "latency_ms": latency,
            "message": f"Koneksi ke basis data {db_type.upper()} berhasil."
        }
    except Exception as e:
        db_result = {
            "status": "error",
            "error": str(e),
            "message": "Gagal terhubung ke database."
        }

    # 2. Cek Koneksi Supabase SDK (jika SUPABASE_URL & KEY diisi)
    supabase_result = {}
    supabase_key = settings.effective_supabase_key
    if settings.SUPABASE_URL and supabase_key:
        supa_start = time.time()
        try:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, supabase_key)
            # Cek akses storage buckets sebagai ping verifikasi kredensial
            buckets = client.storage.list_buckets()
            supa_latency = round((time.time() - supa_start) * 1000, 2)
            supabase_result = {
                "status": "connected",
                "url": settings.SUPABASE_URL,
                "latency_ms": supa_latency,
                "buckets_detected": [b.name for b in buckets],
                "message": "Koneksi ke Supabase SDK berhasil diverifikasi."
            }
        except Exception as e:
            supabase_result = {
                "status": "error",
                "url": settings.SUPABASE_URL,
                "error": str(e),
                "message": "Gagal menghubungi Supabase dengan SUPABASE_URL / SUPABASE_KEY yang diberikan."
            }
    else:
        supabase_result = {
            "status": "not_configured",
            "message": "SUPABASE_URL atau SUPABASE_KEY belum diisi di file .env."
        }

    overall_ok = db_result.get("status") == "connected" and supabase_result.get("status") in ["connected", "not_configured"]

    return {
        "status": "healthy" if overall_ok else "degraded",
        "database": db_result,
        "supabase": supabase_result
    }
