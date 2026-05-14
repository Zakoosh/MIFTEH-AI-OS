"""
validation_steps.py — Generates validation sequences for execution plans.

Each task type maps to an ordered set of validation checks covering
functional, performance, security, regression, and UX dimensions.
"""

from __future__ import annotations

from .models import (
    ValidationStep, ValidationSequence,
    VALIDATION_FUNCTIONAL, VALIDATION_PERFORMANCE,
    VALIDATION_SECURITY, VALIDATION_REGRESSION, VALIDATION_UX,
)


# ---------------------------------------------------------------------------
# Validation templates
# (title, description, type, checks, pass_criteria, blocking, hours, role)
# ---------------------------------------------------------------------------

_V = tuple[str, str, str, list[str], str, bool, float, str]


def _func(title: str, checks: list[str], role: str = "qa-engineer") -> _V:
    return (title, "Functional validation checkpoint.", VALIDATION_FUNCTIONAL,
            checks, "All checks pass without errors.", True, 2.0, role)


def _perf(title: str, checks: list[str], role: str = "engineering-performance-optimizer") -> _V:
    return (title, "Performance validation checkpoint.", VALIDATION_PERFORMANCE,
            checks, "All metrics within SLO thresholds.", True, 2.0, role)


def _sec(title: str, checks: list[str]) -> _V:
    return (title, "Security validation checkpoint.", VALIDATION_SECURITY,
            checks, "No high or critical findings.", True, 2.0, "engineering-backend-developer")


def _reg(title: str, checks: list[str]) -> _V:
    return (title, "Regression validation checkpoint.", VALIDATION_REGRESSION,
            checks, "No regressions introduced.", True, 1.5, "qa-engineer")


def _ux(title: str, checks: list[str]) -> _V:
    return (title, "UX and accessibility checkpoint.", VALIDATION_UX,
            checks, "Meets WCAG 2.1 AA and design spec.", False, 2.0, "ux-designer")


_VALIDATIONS: dict[str, list[_V]] = {

    "seo_campaign": [
        _func("Metadata validation", [
            "Title tag ≤ 60 characters and includes primary keyword",
            "Meta description ≤ 160 characters",
            "Open Graph title and image present",
            "Twitter Card tags valid",
        ], "marketing-seo-specialist"),
        _func("Structured data validation", [
            "JSON-LD validates with schema.org validator",
            "Correct @type used (GameApplication / Article / BreadcrumbList)",
            "No structured data errors in Google Search Console",
        ], "marketing-seo-specialist"),
        _perf("Core Web Vitals check", [
            "LCP < 2.5 s on 3G / mobile",
            "CLS < 0.1",
            "FID / INP < 200 ms",
        ], "marketing-seo-specialist"),
        _reg("Existing page regression", [
            "Homepage still loads with HTTP 200",
            "Category pages not missing canonical tags",
            "Sitemap contains all new URLs",
        ]),
    ],

    "feature": [
        _func("API contract validation", [
            "All endpoints return correct HTTP status codes",
            "Response schema matches OpenAPI spec",
            "Pagination, filtering, and sorting work correctly",
            "Error responses include structured error codes",
        ]),
        _func("Acceptance criteria", [
            "All AC items from spec checked off",
            "Edge cases handled (empty state, max payload)",
            "Feature flag can disable feature without errors",
        ]),
        _perf("Performance baseline", [
            "p95 response time < 300 ms under 100 RPS",
            "No N+1 queries",
            "Memory usage within baseline ± 10%",
        ]),
        _sec("Security review", [
            "Authentication required where expected",
            "No SQL injection vectors (parameterised queries used)",
            "Input validated and sanitised",
            "No sensitive data in logs",
        ]),
        _reg("Regression suite", [
            "Existing integration tests pass (0 failures)",
            "No change to public API contracts",
            "Monitoring alerts not firing after deploy",
        ]),
        _ux("UX acceptance", [
            "Loading states present (skeleton / spinner)",
            "Error states display user-friendly messages",
            "Focus management correct for keyboard navigation",
        ]),
    ],

    "implementation": [
        _func("System integration", [
            "All integration endpoints return expected responses",
            "Health check endpoint returns HTTP 200",
            "Configuration loaded from environment (no hardcoded secrets)",
        ]),
        _perf("Load test", [
            "Sustained 500 RPS with < 1% error rate",
            "p99 latency < 500 ms",
            "No memory leaks over 10-minute soak test",
        ]),
        _sec("Security audit", [
            "OWASP dependency audit clean",
            "Secrets stored in vault / env vars only",
            "No unnecessary open ports or services",
        ]),
        _reg("Smoke regression", [
            "All downstream services unaffected",
            "Rollback tested and confirmed < 5 min RTO",
        ]),
    ],

    "dashboard": [
        _func("Data accuracy", [
            "Dashboard values match source API to 4 decimal places",
            "Real-time updates received within widget refresh_interval",
            "Empty / loading states shown when data unavailable",
        ]),
        _perf("Render performance", [
            "Initial dashboard load < 1.5 s on LTE",
            "Widget reflow does not cause CLS > 0.05",
            "No main-thread blocking > 50 ms",
        ]),
        _ux("Responsive layout", [
            "Dashboard usable on 375 px wide mobile viewport",
            "All interactive elements ≥ 44 px touch target",
            "Keyboard navigation reaches all widgets",
        ]),
        _reg("Dashboard regression", [
            "Other dashboard widgets unaffected",
            "Browser console free of errors",
        ]),
    ],

    "widget": [
        _func("Widget data validation", [
            "Widget renders correct data from backend API",
            "Refresh cycle updates data without full page reload",
            "Error boundary catches backend failures gracefully",
        ]),
        _perf("Widget load time", [
            "Widget visible < 800 ms after parent mounts",
            "No unnecessary re-renders",
        ]),
        _reg("Widget isolation", [
            "Other widgets unaffected when this widget errors",
            "Widget can be disabled via feature flag",
        ]),
    ],

    "watchlist": [
        _func("CRUD validation", [
            "Create / update / delete watchlist items work correctly",
            "Alert rules persist across sessions",
            "Ticker autocomplete returns results in < 200 ms",
        ]),
        _func("Alert delivery", [
            "Push notification delivered within 30 s of trigger condition",
            "Email alert delivered within 2 min",
            "Alert not repeated after user snoozes",
        ]),
        _reg("Watchlist regression", [
            "Existing watchlists unaffected by new items",
            "No duplicate alert triggers",
        ]),
    ],

    "analytics": [
        _func("Computation accuracy", [
            "Metrics match manual calculation on test dataset",
            "Time-zone handling correct for all supported regions",
            "Aggregations consistent across date range selections",
        ]),
        _perf("Query performance", [
            "Analytics endpoint responds < 500 ms for 90-day range",
            "No full-table scans; queries use appropriate indices",
        ]),
        _reg("Analytics regression", [
            "Historical data not altered by new computation",
            "Existing chart components unaffected",
        ]),
    ],

    "ux": [
        _ux("Design fidelity", [
            "Implementation matches Figma designs within 4 px / 1 colour step",
            "Transitions and animations match interaction spec",
        ]),
        _ux("Accessibility", [
            "WCAG 2.1 AA audit with axe-core: 0 critical violations",
            "Screen reader announces component state changes correctly",
            "Colour contrast ratio ≥ 4.5:1 for all text",
        ]),
        _reg("Cross-browser regression", [
            "Renders correctly in Chrome, Firefox, Safari, Edge",
            "Mobile Safari layout not broken",
        ]),
    ],

    "monetization": [
        _func("Payment flow", [
            "Stripe checkout completes without error in test mode",
            "Subscription created and reflected in user account immediately",
            "Cancellation and refund flows work correctly",
        ]),
        _sec("Payment security", [
            "No card data touches application servers (Stripe Elements only)",
            "HTTPS enforced on all billing pages",
            "Webhook signature verification active",
        ]),
        _reg("Billing regression", [
            "Free users unaffected by premium gate logic",
            "Existing subscribers not downgraded",
        ]),
    ],

    "optimization": [
        _func("Experiment integrity", [
            "Traffic correctly split between variants",
            "Tracking events fire for impression and conversion",
            "No sample pollution between variants",
        ]),
        _reg("Variant regression", [
            "Control variant identical to pre-experiment baseline",
            "No JavaScript errors introduced by experiment code",
        ]),
    ],
}

# Fallback for types not explicitly mapped
_VALIDATIONS["campaign"]    = _VALIDATIONS["seo_campaign"]
_VALIDATIONS["content"]     = _VALIDATIONS["seo_campaign"][:2]
_VALIDATIONS["roadmap"]     = [
    _func("Roadmap completeness", [
        "All milestones have success criteria defined",
        "No work items without assigned quarter",
    ], "product-manager"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_validation_sequence(
    plan_id: str,
    work_item_id: str,
    project: str,
    task_type: str,
    title: str,
) -> ValidationSequence:
    templates = _VALIDATIONS.get(task_type, _VALIDATIONS["feature"])
    steps: list[ValidationStep] = []
    for seq, (vt, desc, vtype, checks, criteria, blocking, hours, role) in enumerate(
        templates, start=1
    ):
        steps.append(ValidationStep(
            validation_id  = f"val_{work_item_id}_{seq:02d}",
            plan_id        = plan_id,
            step_sequence  = seq,
            title          = vt,
            description    = desc,
            validation_type= vtype,
            checks         = checks,
            pass_criteria  = criteria,
            blocking       = blocking,
            estimated_hours= hours,
            assigned_role  = role,
        ))

    total_h = sum(s.estimated_hours for s in steps)
    blocking = sum(1 for s in steps if s.blocking)

    return ValidationSequence(
        sequence_id          = f"vs_{work_item_id}",
        plan_id              = plan_id,
        work_item_id         = work_item_id,
        project              = project,
        title                = f"Validation: {title}",
        steps                = [s.to_dict() for s in steps],
        total_steps          = len(steps),
        total_blocking_steps = blocking,
        estimated_hours      = round(total_h, 1),
    )
