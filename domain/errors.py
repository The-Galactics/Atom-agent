class DomainError(Exception):
    pass


class DomainValidationError(DomainError):
    pass


class ProviderError(DomainError):
    pass
