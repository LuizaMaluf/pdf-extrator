from uuid import UUID


class ExtractionOrchestrator:
    """Coordena o pipeline de extração — sem lógica de negócio própria."""

    async def run(self, job_id: UUID) -> None:
        raise NotImplementedError
