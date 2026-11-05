from app.schemas.auth import UserRegister, UserLogin, UserResponse, Token
from app.schemas.device import DeviceRegister, DeviceResponse
from app.schemas.config import ConfigUpdate, ConfigResponse
from app.schemas.road_class import RoadClassCreate, RoadClassResponse
from app.schemas.report import (
    ReportResponse,
    ReportParameterResponse,
    ReportStatusUpdate,
    StatusLogResponse,
    ReportMapItem,
    ReportSummaryResponse,
    RecalculateResponse
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "Token",
    "DeviceRegister",
    "DeviceResponse",
    "ConfigUpdate",
    "ConfigResponse",
    "RoadClassCreate",
    "RoadClassResponse",
    "ReportResponse",
    "ReportParameterResponse",
    "ReportStatusUpdate",
    "StatusLogResponse",
    "ReportMapItem",
    "ReportSummaryResponse",
    "RecalculateResponse",
]

