class DomainNotFoundError(Exception):
    def __init__(self, domain_id: object) -> None:
        super().__init__(f"Domain not found: {domain_id}")
        self.domain_id = domain_id


class LowConfidenceError(Exception):
    def __init__(self, confidence: float, threshold: float) -> None:
        super().__init__(f"Confidence {confidence:.2f} below threshold {threshold:.2f}")
        self.confidence = confidence
        self.threshold = threshold


class SchemaValidationError(Exception):
    pass


class ExtractionFailedError(Exception):
    pass


class ClaudeAPIRateLimitError(Exception):
    pass


class PDFProcessingError(Exception):
    pass
