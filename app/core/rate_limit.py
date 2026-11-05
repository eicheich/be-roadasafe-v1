import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, status
from app.core.config import settings

class DeviceRateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()

    def check_rate_limit(self, device_id: str) -> bool:
        current_time = time.time()
        with self.lock:
            # Purge timestamps outside the window
            timestamps = self.requests[device_id]
            cutoff = current_time - self.window_seconds
            self.requests[device_id] = [ts for ts in timestamps if ts > cutoff]
            
            if len(self.requests[device_id]) >= self.max_requests:
                return False
            
            self.requests[device_id].append(current_time)
            return True


rate_limiter = DeviceRateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)


def verify_device_rate_limit(device_id: str):
    if not rate_limiter.check_rate_limit(device_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Terlalu banyak permintaan untuk perangkat {device_id}. Batas: {settings.RATE_LIMIT_PER_MINUTE} req/menit."
        )

