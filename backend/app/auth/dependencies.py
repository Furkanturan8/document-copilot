import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthApiError, AuthRetryableError

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    # Kept so request-scoped Supabase clients can act as this user under RLS.
    access_token: str


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized("Missing bearer token")

    try:
        response = await request.app.state.supabase.auth.get_user(credentials.credentials)
    except AuthRetryableError as error:
        # Supabase unreachable: not the caller's fault, so don't make the client drop its session.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Auth service unavailable") from error
    except AuthApiError as error:
        raise _unauthorized("Invalid or expired token") from error

    # Email is the only sign-in method, and users.email is NOT NULL.
    if response is None or not response.user.email:
        raise _unauthorized("Invalid or expired token")

    return CurrentUser(
        id=uuid.UUID(response.user.id),
        email=response.user.email,
        access_token=credentials.credentials,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
