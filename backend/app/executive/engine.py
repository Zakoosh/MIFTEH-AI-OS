from app.executive.business_metrics import build_business_metrics
from app.executive.company_priorities import build_company_priorities, company_focus
from app.executive.executive_memory import build_memory_signals
from app.executive.focus_engine import build_focus_recommendations, highest_priority_project
from app.executive.models import (
    BusinessMetricList,
    ExecutiveOverview,
    ExecutivePriorityList,
    ExecutiveRecommendationList,
)
from app.executive.optimization_balance import build_optimization_balance
from app.executive.portfolio_manager import load_portfolio_context
from app.executive.resource_allocator import allocate_resources


def _executive_context() -> dict:
    context = load_portfolio_context()
    strategy = context["strategy"]
    memory = context["memory"]
    orchestrator = context["orchestrator"]
    priorities = build_company_priorities(strategy)
    resources = allocate_resources(strategy.projects)
    focus = company_focus(priorities)
    highest = highest_priority_project(resources.resource_distribution, priorities)
    recommendations = build_focus_recommendations(
        company_focus=focus,
        highest_project=highest,
        resource_distribution=resources.resource_distribution,
        priorities=priorities,
    )
    metrics = build_business_metrics(strategy, memory, orchestrator)
    balance = build_optimization_balance(strategy, priorities, resources.resource_distribution)
    memory_signals = build_memory_signals(memory)

    return {
        "strategy": strategy,
        "memory": memory,
        "orchestrator": orchestrator,
        "priorities": priorities,
        "resources": resources,
        "company_focus": focus,
        "highest_priority_project": highest,
        "recommendations": recommendations,
        "metrics": metrics,
        "balance": balance,
        "memory_signals": memory_signals,
    }


def executive_overview() -> ExecutiveOverview:
    context = _executive_context()
    return ExecutiveOverview(
        company_focus=context["company_focus"],
        highest_priority_project=context["highest_priority_project"],
        resource_distribution=context["resources"].resource_distribution,
        recommendations=context["recommendations"],
        priorities=context["priorities"],
        metrics=context["metrics"],
        optimization_balance=context["balance"],
    )


def executive_priorities() -> ExecutivePriorityList:
    return ExecutivePriorityList(priorities=_executive_context()["priorities"])


def executive_resources():
    return _executive_context()["resources"]


def executive_recommendations() -> ExecutiveRecommendationList:
    return ExecutiveRecommendationList(recommendations=_executive_context()["recommendations"])


def executive_metrics() -> BusinessMetricList:
    context = _executive_context()
    return BusinessMetricList(
        metrics=context["metrics"],
        memory_signals=context["memory_signals"],
    )
