from app.production.models import MiftehRecommendation


def landing_recommendations() -> list[MiftehRecommendation]:
    return [
        MiftehRecommendation(
            landing_recommendation="Add AI automation showcase section to improve conversions",
            domain="conversion",
            expected_impact=86,
            rationale=[
                "Main site is business-facing acquisition layer",
                "Executive strategy prioritizes growth and conversion",
            ],
        ),
        MiftehRecommendation(
            landing_recommendation="Add proof-of-work cards for orchestration, memory, strategy, and executive layers",
            domain="branding",
            expected_impact=82,
            rationale=["Turns platform capabilities into trust signals"],
        ),
    ]
