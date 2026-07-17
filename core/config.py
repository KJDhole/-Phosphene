"""
共享配置 — 加载配置、项目根路径、控制台
"""

from __future__ import annotations
import os
import yaml
from copy import deepcopy
from pathlib import Path
from datetime import timezone, timedelta
from core.console import FailureSafeConsole

# 项目根目录
ROOT = Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
CONSOLE = FailureSafeConsole()
BJT = timezone(timedelta(hours=8))

# 加载 .env 文件（如果存在）
_env_file = ROOT / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip().strip("\"'")
                if _k and not os.environ.get(_k):
                    os.environ[_k] = _v

# 配置缓存
_config_cache: dict | None = None
_config_mtime: float = 0


def load_config() -> dict:
    """加载并校验配置（带缓存，文件变更时自动重载）"""
    global _config_cache, _config_mtime

    # 检查文件是否变更
    try:
        current_mtime = CONFIG_PATH.stat().st_mtime
    except OSError:
        current_mtime = 0

    if _config_cache is not None and abs(current_mtime - _config_mtime) < 2.0:
        return deepcopy(_config_cache)

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError("配置文件根节点必须是对象")
    for required in ("ai", "output", "runtime"):
        if not isinstance(config.get(required), dict):
            raise ValueError(f"配置缺少必填对象: {required}")
    if not str(config["ai"].get("base_url", "")).startswith("https://"):
        raise ValueError("ai.base_url 必须使用 HTTPS")
    if not config["ai"].get("model"):
        raise ValueError("配置缺少 ai.model")

    _config_cache = config
    _config_mtime = current_mtime
    return deepcopy(config)
