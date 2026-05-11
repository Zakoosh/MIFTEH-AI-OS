from app.memory_ai.learning_engine import build_memory_snapshot
from app.orchestrator.engine import orchestrator_status
from app.strategy.engine import strategy_overview


def load_portfolio_context() -> dict:
    return {
        "strategy": strategy_overview(),
        "memory": build_memory_snapshot(),
        "orchestrator": orchestrator_status(),
    }
