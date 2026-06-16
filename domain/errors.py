class DomainError(Exception):
    # Base domain-layer exception.
    pass


class DomainValidationError(DomainError):
    # Raised when domain validation fails.
    pass


class ProviderError(DomainError):
    # Raised when an external provider fails.
    pass
