from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.dependencies import CurrentUserDep

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(BaseModel):
    id: str
    email: str


@router.get("/me")
async def me(user: CurrentUserDep) -> MeResponse:
    return MeResponse(id=str(user.id), email=user.email)
