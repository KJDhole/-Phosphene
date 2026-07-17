"""捕获 stdout → WebSocket 广播 (同步上下文用)"""

import sys
import asyncio
from typing import Callable


class LogCapture:
    """替换 sys.stdout，将 print 输出转发到 WebSocket 广播"""

    def __init__(self, broadcast_fn: Callable, category: str):
        self._broadcast = broadcast_fn
        self._category = category
        self._buffer = ""
        self._old_stdout = sys.stdout

    def write(self, text: str):
        self._buffer += text
        if "\n" in text or len(self._buffer) > 100:
            line = self._buffer.strip()
            if line:
                asyncio.create_task(self._broadcast(self._category, "info", line))
            self._buffer = ""

    def flush(self):
        if self._buffer.strip():
            asyncio.create_task(self._broadcast(self._category, "info", self._buffer.strip()))
            self._buffer = ""

    def __enter__(self):
        sys.stdout = self
        return self

    def __exit__(self, *args):
        self.flush()
        sys.stdout = self._old_stdout
