from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.device import DeviceRegister, DeviceResponse
from app.api.deps import get_current_user, get_current_admin

router = APIRouter()


@router.post("/register", response_model=DeviceResponse)
def register_device(
    device_in: DeviceRegister,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Pendaftaran atau pembaruan data perangkat mobile pengemudi/pelapor.
    """
    device = db.query(Device).filter(Device.id == device_in.id).first()
    if device:
        if device_in.model_perangkat:
            device.model_perangkat = device_in.model_perangkat
        if device_in.versi_app:
            device.versi_app = device_in.versi_app
        if current_user:
            device.user_id = current_user.id
        device.is_active = True
    else:
        device = Device(
            id=device_in.id,
            user_id=current_user.id if current_user else None,
            model_perangkat=device_in.model_perangkat,
            versi_app=device_in.versi_app,
            is_active=True
        )
        db.add(device)
    
    db.commit()
    db.refresh(device)
    return device


@router.get("/", response_model=List[DeviceResponse])
def list_devices(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Admin: Mendapatkan daftar perangkat terdaftar.
    """
    return db.query(Device).all()


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Perangkat {device_id} tidak ditemukan"
        )
    return device

