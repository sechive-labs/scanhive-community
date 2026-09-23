import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings


class SlidingWindowLimiter:
    """In-process sliding-window limiter.

    State is per worker process, so with N workers the effective ceiling is N
    times the limit. Per-account limits that must hold globally live in the
    database instead (see PasswordResetService).
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        """Records a hit. Returns None if allowed, else seconds until retry."""
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > 10_000:
                self._evict(now)
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, int(self.window - (now - hits[0])))
            hits.append(now)
            return None

    def blocked(self, key: str) -> int | None:
        """Like check() but records nothing: seconds until retry if over the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.get(key)
            if not hits:
                return None
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, int(self.window - (now - hits[0])))
            return None

    def hit(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def _evict(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "")
        candidate = forwarded.split(",")[-1].strip() if forwarded else ""
        if candidate:
            return candidate[:45]
    return request.client.host if request.client else "unknown"


def enforce(limiter: SlidingWindowLimiter, key: str) -> None:
    retry_after = limiter.check(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_blocked(limiter: SlidingWindowLimiter, key: str) -> None:
    retry_after = limiter.blocked(key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


# Sign-in: every attempt counts against the IP; only failures count against
# an (IP, email) pair, so an attacker can't lock a victim out from elsewhere.
login_ip_limiter = SlidingWindowLimiter(limit=30, window_seconds=15 * 60)
login_failure_limiter = SlidingWindowLimiter(limit=5, window_seconds=15 * 60)
register_limiter = SlidingWindowLimiter(limit=5, window_seconds=60 * 60)
verify_email_limiter = SlidingWindowLimiter(limit=10, window_seconds=15 * 60)
resend_verification_limiter = SlidingWindowLimiter(limit=10, window_seconds=15 * 60)
# Caps "you already have an account" notices sent to one address.
existing_account_notice_limiter = SlidingWindowLimiter(limit=1, window_seconds=60 * 60)
forgot_password_limiter = SlidingWindowLimiter(limit=10, window_seconds=15 * 60)
reset_password_limiter = SlidingWindowLimiter(limit=10, window_seconds=15 * 60)
