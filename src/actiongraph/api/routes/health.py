from fastapi import APIRouter, Depends

from actiongraph import __version__
from actiongraph.api.deps import get_settings
from actiongraph.config import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Liveness check used by monitoring (and the UI header)."""
    model = settings.anthropic_model if settings.llm_provider == "anthropic" else "rule-based-v1"
    return {
        "status": "ok",
        "version": __version__,
        "llm_provider": settings.llm_provider,
        "model": model,
    }
