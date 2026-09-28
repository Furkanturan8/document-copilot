from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import settings


async def create_user_client(access_token: str) -> AsyncClient:
    # The user's JWT replaces the anon key as the bearer, so RLS policies apply to this user.
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_anon_key.get_secret_value(),
        options=AsyncClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
            auto_refresh_token=False,
            persist_session=False,
        ),
    )


async def create_service_client() -> AsyncClient:
    # Bypasses RLS: every write through this client must be scoped to the authenticated user.
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_service_role_key.get_secret_value(),
        options=AsyncClientOptions(auto_refresh_token=False, persist_session=False),
    )
