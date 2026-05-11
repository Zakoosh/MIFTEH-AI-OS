# MIFTEH AI OS Production Deployment Plan

## Architecture decision

For the current production phase, MIFTEH AI OS should be embedded inside the existing MIFTEH Admin Panel instead of deployed as a standalone platform.

Target routes:
- `mifteh.com/admin/ai-os`
- `mifteh.com/admin/os`

The admin panel becomes the unified AI-powered operations center for:
- AI dashboard
- orchestration monitoring
- executive insights
- mission control
- reports
- automation visibility
- strategy insights

## Admin integration model

The AI OS dashboard remains modular and portable:
- Dashboard assets stay in `frontend/dashboard/`.
- The backend serves protected admin routes from `/admin/ai-os/` and `/admin/os/`.
- The dashboard API base URL resolves to the same origin in admin production and to `http://127.0.0.1:8000` on the local static dev server.
- Future standalone deployment to Vercel, Railway, or another host remains possible because the dashboard is still isolated from admin-specific implementation details.

## Authentication

Admin access must use secure session-based authentication.

Required environment variables:
- `MIFTEH_AI_ADMIN_EMAIL`
- `MIFTEH_AI_ADMIN_PASSWORD`

Current admin owner:
- `zalbeltaji@gmail.com`

Rules:
- Do not hardcode credentials.
- Do not commit `.env` values.
- Use environment variables only.
- Store the admin session in an HTTP-only cookie.
- Redirect unauthenticated browser users to `/admin/login`.
- Return `401` JSON for unauthorized non-browser requests.

## Route protection

Protected routes:
- `/admin/ai-os`
- `/admin/ai-os/`
- `/admin/ai-os/*`
- `/admin/os`
- `/admin/os/`
- `/admin/os/*`

Support routes:
- `/admin/login`
- `/admin/logout`
- `/admin/session`

The session validation middleware is intentionally isolated so it can later be replaced by the production admin panel session provider.

## Future RBAC and multi-user support

The current implementation supports one environment-configured admin identity.

Future extensions should add:
- admin user table or identity provider integration
- roles such as owner, operator, analyst, viewer
- route-level permissions
- per-project access policies
- audit log entries for mission runs, automation changes, and git operations

## Dashboard navigation

The existing admin sidebar should add an AI OS navigation item:
- Label: `AI OS`
- Target: `/admin/ai-os`
- Alternate target: `/admin/os`

The embedded dashboard should preserve MIFTEH branding and continue to expose:
- System Overview
- Projects Monitor
- Mission Control
- AI Decisions
- Reports Center
- Git Activity
- Automation
- Orchestrator
- Adaptive Memory
- Strategy
- Executive

## Deployment abstraction

Keep deployment modular:
- Admin embedded mode is the default now.
- Standalone deployment remains a future option.
- Environment-specific API base URLs should be injected through `window.MIFTEH_API_BASE_URL` when needed.
- No business logic should be duplicated between admin and standalone modes.

## Validation checklist

Before production release:
- Unauthenticated `/admin/ai-os/` redirects to `/admin/login`.
- Invalid login is rejected.
- Valid environment-configured login sets an HTTP-only session cookie.
- Authenticated `/admin/ai-os/` loads the dashboard.
- `/admin/session` reports session state.
- Dashboard API calls work from the admin route.
- Existing local static dashboard still works.
- No hardcoded secrets exist in code or docs.
- Admin sidebar links to the AI OS route.
