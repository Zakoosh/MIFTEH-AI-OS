from fastapi import APIRouter

from app.memory_ai.learning_engine import (
    memory_failures,
    memory_heuristics,
    memory_patterns,
    memory_recommendations,
    memory_successes,
)
from app.memory_ai.models import (
    FailureCollection,
    HeuristicCollection,
    MemoryCollection,
    RecommendationCollection,
    SuccessCollection,
)


router = APIRouter(prefix="/memory-ai", tags=["memory-ai"])


@router.get("/patterns")
def get_memory_patterns():
    return MemoryCollection(patterns=memory_patterns()).model_dump()


@router.get("/successes")
def get_memory_successes():
    return SuccessCollection(successes=memory_successes()).model_dump()


@router.get("/failures")
def get_memory_failures():
    return FailureCollection(failures=memory_failures()).model_dump()


@router.get("/recommendations")
def get_memory_recommendations():
    return RecommendationCollection(recommendations=memory_recommendations()).model_dump()


@router.get("/heuristics")
def get_memory_heuristics():
    return HeuristicCollection(heuristics=memory_heuristics()).model_dump()
