"""Rich console that can never take down a background pipeline."""

from __future__ import annotations

from typing import Any

from rich.console import Console


class FailureSafeConsole(Console):
    """Treat terminal rendering as optional and record failures diagnostically."""

    def print(self, *objects: Any, **kwargs: Any) -> None:
        try:
            super().print(*objects, **kwargs)
        except Exception as exc:
            try:
                from core.diagnostics import diagnostic_exception

                diagnostic_exception(
                    "console.write_failed",
                    exc,
                    object_types=[type(item).__name__ for item in objects],
                )
            except Exception:
                pass
