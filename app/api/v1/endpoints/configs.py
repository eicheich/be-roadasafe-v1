from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.config import ConfigUpdate, ConfigResponse
from app.services.urgency_service import UrgencyService
from app.api.deps import get_current_admin

router = APIRouter()


@router.get("/", response_model=ConfigResponse)
def get_config(db: Session = Depends(get_db)):
    """
    Mengambil konfigurasi sistem aktif (bobot parameter L, K, P, T, ambang skor, versi model).
    """
    return UrgencyService.get_active_config(db)


@router.put("/", response_model=ConfigResponse)
def update_config(
    config_in: ConfigUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Admin (UC-04 / FR-23): Memperbarui bobot, ambang batas urgensi, dan versi model.
    """
    config = UrgencyService.get_active_config(db)
    
    if config_in.bobot_L is not None:
        config.bobot_L = config_in.bobot_L
    if config_in.bobot_K is not None:
        config.bobot_K = config_in.bobot_K
    if config_in.bobot_P is not None:
        config.bobot_P = config_in.bobot_P
    if config_in.bobot_T is not None:
        config.bobot_T = config_in.bobot_T
    if config_in.ambang_low is not None:
        config.ambang_low = config_in.ambang_low
    if config_in.ambang_medium is not None:
        config.ambang_medium = config_in.ambang_medium
    if config_in.versi_model_aktif is not None:
        config.versi_model_aktif = config_in.versi_model_aktif

    db.commit()
    db.refresh(config)
    return config

