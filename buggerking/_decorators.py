# buggerking/_decorators.py
import functools
import logging

log = logging.getLogger(__name__)

def wrap_debugpy(func):
    """debugpy 함수를 buggerking 전용 래퍼로 감싼다."""
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # ── pre-hook: 호출 직전 처리 ───────────────────────
        log.debug("⚙️  %s ← args=%s kwargs=%s", func.__name__, args, kwargs)
        # 예: 원격 재접속 토큰 갱신, 트레이싱 설정 등
        
        try:
            return func(*args, **kwargs)          # debugpy 원본 호출
        finally:
            # ── post-hook: 호출 직후 처리 ──────────────────
            log.debug("✅  %s 완료", func.__name__)
            # 예: 리소스 정리·복원, 오류 상태 리셋 등
    return _wrapper
