from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class SchemaRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, domain_id: UUID) -> object:
        raise NotImplementedError

    async def get_version(self, domain_id: UUID, version: int) -> object:
        raise NotImplementedError

    async def add_field(self, domain_id: UUID, field: object) -> object:
        raise NotImplementedError

    async def deprecate_field(self, domain_id: UUID, field_name: str) -> object:
        raise NotImplementedError

    async def validate(self, domain_id: UUID) -> object:
        raise NotImplementedError
