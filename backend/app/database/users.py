from supabase import AsyncClient

from app.auth.dependencies import CurrentUser


async def ensure_user(service_client: AsyncClient, user: CurrentUser) -> None:
    # Service role because RLS gives users no insert policy on their own profile row.
    await (
        service_client.table("users")
        .upsert({"id": str(user.id), "email": user.email}, on_conflict="id")
        .execute()
    )
