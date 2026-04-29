# Public API re-exports (lazy — imports trigger neo4j dependency on use):
__all__ = ["ContextRetriever", "ContextObject"]


def __getattr__(name):  # type: ignore[no-untyped-def]
    if name in __all__:
        from agents.retrieval.pipeline import ContextObject, ContextRetriever
        return {"ContextRetriever": ContextRetriever, "ContextObject": ContextObject}[name]
    raise AttributeError(name)
