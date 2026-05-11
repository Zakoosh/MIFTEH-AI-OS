from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from app.admin.config import SESSION_COOKIE_NAME
from app.admin.session import validate_session_token


PROTECTED_PREFIXES = (
    "/admin/os",
)


class AdminSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        if not path.startswith(PROTECTED_PREFIXES):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE_NAME)
        if validate_session_token(token):
            return await call_next(request)

        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            next_path = request.url.path
            return RedirectResponse(
                url=f"/admin/login?next={next_path}",
                status_code=303,
            )

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": "Unauthorized admin session",
            },
        )
