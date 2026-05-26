"""LangGraph transcript analysis pipelines (Phase A+)."""

__all__ = ["get_compiled_graph"]


def get_compiled_graph():
    from app.graphs.parent import get_compiled_graph as _get

    return _get()
