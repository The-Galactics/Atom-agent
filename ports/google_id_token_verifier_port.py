from abc import ABC, abstractmethod
from domain.auth.models import GoogleIdentity


class GoogleIdTokenVerifierPort(ABC):
    # Contract for verifying a Google OIDC ID token.
    @abstractmethod
    def verify(self, raw_id_token: str) -> GoogleIdentity:
        """Verifies signature, issuer, audience, expiry and email_verified.

        Returns the verified identity, or raises AuthenticationError when the token
        is invalid or the email is not verified.
        """
        pass
