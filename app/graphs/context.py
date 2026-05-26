"""Runtime context for LangGraph nodes (avoids circular imports)."""

from __future__ import annotations

from contextvars import ContextVar

from app.config import Settings

_graph_settings: ContextVar[Settings | None] = ContextVar("_graph_settings", default=None)


def set_graph_settings(settings: Settings):
    return _graph_settings.set(settings)


def reset_graph_settings(token) -> None:
    _graph_settings.reset(token)


def get_graph_settings() -> Settings:
    settings = _graph_settings.get()
    if settings is None:
        raise RuntimeError("LangGraph settings context is not set.")
    return settings
