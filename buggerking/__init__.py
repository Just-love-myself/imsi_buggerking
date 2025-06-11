# from .core import debug
# from .init import init -> 필요한가?

import _debugpy as _dbg
from _decorators import debug_decorator
        

__all__ = _dbg.__all__  # debugpy에서 정의된 공개 API 목록 재사용

# __all__에 정의된 항목을 buggerking 네임스페이스로 그대로 내보냄
for name in __all__:
    globals()[name] = getattr(_dbg, name)
    


__all__.append('debug_decorator')

