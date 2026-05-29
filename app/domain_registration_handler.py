from sqlalchemy.ext.asyncio import AsyncSession


class DomainRegistrationHandler:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, registration: object) -> object:
        raise NotImplementedError
