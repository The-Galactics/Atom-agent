class DomainError(Exception):
    # Base domain-layer exception.
    pass


class DomainValidationError(DomainError):
    # Raised when domain validation fails.
    pass


class ProviderError(DomainError):
    # Raised when an external provider fails.
    pass


class AuthenticationError(DomainError):
    # Raised when credentials are invalid or authentication fails. The message is
    # deliberately generic so it never reveals whether the email exists.
    pass


class UserAlreadyExistsError(DomainError):
    # Raised when registering an email that already has an account.
    pass


class InvalidTokenError(DomainError):
    # Raised when a session/refresh token is missing, malformed, expired or revoked.
    pass
