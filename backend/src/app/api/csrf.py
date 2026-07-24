"""CSRF dependency for cookie-authenticated routes.

We use the classic double-submit pattern: a non-httpOnly cookie
``factorial_csrf`` is set at login, and the SPA mirrors it into an
``X-CSRF-Token`` header on every state-changing request. The server
just compares the two via constant-time equality. No server-side
state is needed; an attacker who can't read the cookie can't forge
the header.

Combined with ``SameSite=Lax``, this defends against the classic CSRF
attack: cross-origin POSTs from a malicious page won't include the
cookie, and same-origin scripts on a different tab can't read it from
JavaScript without the host being attacker-controlled.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.services.session_service import csrf_tokens_match

CSRF_COOKIE_NAME = "factorial_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Methods that require CSRF protection. GET/HEAD/OPTIONS are read-only and
# CSRF-safe; SSE chat is a GET, exempt by design.
_PROTECTED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


async def require_csrf(request: Request) -> None:
    """Reject state-changing requests without a matching CSRF token.

    Two carve-outs live inside this function:

    * Safe HTTP methods (anything outside ``_PROTECTED_METHODS``) return
      immediately — GET / HEAD / OPTIONS are read-only and CSRF-safe.
    * Requests presenting an ``X-API-Key`` header return immediately.
      API-key clients don't have a session cookie and don't need CSRF:
      the header itself is the credential and is not browser-replayable.

    The unauthenticated public-share routes are also CSRF-exempt, but
    that exemption is enforced at the router level (see
    ``api/v1/router.py`` — the ``shares_public`` router is mounted
    without a ``Depends(require_csrf)`` guard), not by any branch in
    this function. From this function's point of view every request it
    actually sees must satisfy one of the two conditions above.
    """
    if request.method not in _PROTECTED_METHODS:
        return

    if request.headers.get("X-API-Key"):
        return

    header_value = request.headers.get(CSRF_HEADER_NAME)
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_tokens_match(header_value, cookie_value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )
