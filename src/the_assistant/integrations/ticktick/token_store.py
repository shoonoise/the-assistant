from __future__ import annotations

from cryptography.fernet import Fernet

from ...db import UserService, get_user_service


class TickTickTokenStore:
    """Store TickTick access tokens encrypted in the database."""

    def __init__(
        self,
        encryption_key: str,
        account: str | None = None,
        user_service: UserService | None = None,
    ) -> None:
        self.fernet = Fernet(encryption_key.encode())
        self.account = account or "default"
        self.user_service = user_service or get_user_service()

    async def get(self, user_id: int) -> str | None:
        enc = await self.user_service.get_ticktick_token(user_id, account=self.account)
        if enc is None:
            return None
        return self.fernet.decrypt(enc.encode()).decode()

    async def save(self, user_id: int, token: str) -> None:
        enc = self.fernet.encrypt(token.encode()).decode()
        await self.user_service.set_ticktick_token(user_id, enc, account=self.account)

    async def delete(self, user_id: int) -> None:
        await self.user_service.set_ticktick_token(user_id, None, account=self.account)
