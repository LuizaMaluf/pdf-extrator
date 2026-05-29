from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class CorrectionProcessor:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process(
        self,
        job_id: UUID,
        corrections: list[object],
        new_fields: list[object],
    ) -> None:
        raise NotImplementedError
