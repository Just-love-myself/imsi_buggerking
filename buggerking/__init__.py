# from .core import debug
# from .init import init -> 필요한가?

import _debugpy as _dbg
from ._decorators import wrap_debugpy  # 버거킹 고유 pre/post 로직

__all__ = _dbg.__all__

# 퍼블릭 API에 대해 함수는 감싸고, 상수는 그대로 export
for name in __all__:
    obj = getattr(_dbg, name)
    if callable(obj):
        globals()[name] = wrap_debugpy(obj)
    else:
        globals()[name] = obj



