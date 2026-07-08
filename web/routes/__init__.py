"""路由注册 — import 子模块以注册路由"""

from fastapi import APIRouter

router = APIRouter(prefix="/api")

# 注册子模块路由（通过 import 触发 @router 装饰器）
from . import categories
from . import run
from . import history
from . import config
from . import video
