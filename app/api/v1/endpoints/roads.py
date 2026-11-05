from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.road_class import RoadClass
from app.models.user import User
from app.schemas.road_class import RoadClassCreate, RoadClassResponse
from app.api.deps import get_current_admin

router = APIRouter()


@router.get("/", response_model=List[RoadClassResponse])
def list_road_classes(db: Session = Depends(get_db)):
    """
    Mendapatkan daftar kelas jalan dan bobot kepadatan (SRS Bagian 5.2 & 7).
    """
    return db.query(RoadClass).all()


@router.post("/", response_model=RoadClassResponse, status_code=status.HTTP_201_CREATED)
def create_road_class(
    road_in: RoadClassCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Admin: Menambahkan data kelas jalan dan bobot kepadatannya.
    """
    road = RoadClass(
        nama_jalan=road_in.nama_jalan,
        kelas=road_in.kelas.lower(),
        bobot_kepadatan=road_in.bobot_kepadatan
    )
    db.add(road)
    db.commit()
    db.refresh(road)
    return road


@router.get("/lookup")
def lookup_road_density(
    nama_jalan: Optional[str] = None,
    kelas: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lookup estimasi nilai parameter kepadatan (T) berdasarkan nama jalan atau kelas jalan:
    Arteri = 100, Kolektor = 60, Lokal = 30 (SRS Bagian 5.2).
    """
    if nama_jalan:
        road = db.query(RoadClass).filter(RoadClass.nama_jalan.ilike(f"%{nama_jalan}%")).first()
        if road:
            return {
                "nama_jalan": road.nama_jalan,
                "kelas": road.kelas,
                "nilai_T": road.bobot_kepadatan
            }

    # Fallback ke kelas default
    defaults = {
        "arteri": 100.0,
        "kolektor": 60.0,
        "lokal": 30.0
    }
    
    if kelas and kelas.lower() in defaults:
        return {
            "nama_jalan": nama_jalan or "Default",
            "kelas": kelas.lower(),
            "nilai_T": defaults[kelas.lower()]
        }

    return {
        "nama_jalan": nama_jalan or "Tidak diketahui",
        "kelas": "lokal",
        "nilai_T": 30.0
    }

