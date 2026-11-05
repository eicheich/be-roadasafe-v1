import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RoadSafe Backend API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "roadasafe-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "sqlite:///./roadasafe.db"
    
    # Supabase (Storage & Integration)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "reports"

    @property
    def effective_supabase_key(self) -> Optional[str]:
        return self.SUPABASE_SERVICE_ROLE_KEY or self.SUPABASE_KEY or self.SUPABASE_ANON_KEY
    
    # File Storage
    UPLOAD_DIR: str = os.path.join(os.getcwd(), "uploads", "reports")
    
    # Deduplication & GPS thresholds
    DEDUPLICATION_RADIUS_METERS: float = 15.0
    MAX_GPS_ACCURACY_METERS: float = 20.0
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
