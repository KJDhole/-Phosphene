"""路由注册 — import 子模块以注册路由"""

from fastapi import APIRouter

router = APIRouter(prefix="/api")

# 注册子模块路由（通过 import 触发 @router 装饰器）
from . import categories  # noqa: E402,F401
from . import run  # noqa: E402,F401
from . import history  # noqa: E402,F401
from . import config  # noqa: E402,F401
from . import video  # noqa: E402,F401
from . import diagnostics  # noqa: E402,F401
