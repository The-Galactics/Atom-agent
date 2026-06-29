from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from domain.auth.models import GoogleIdentity
from domain.errors import AuthenticationError
from ports.google_id_token_verifier_port import GoogleIdTokenVerifierPort

_VALID_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleIdTokenVerifier(GoogleIdTokenVerifierPort):
    """Verifies a Google OIDC ID token using Google's public keys.

    ``verify_oauth2_token`` checks the signature, expiry and that ``aud`` equals
    our ``client_id``. We additionally enforce the issuer and ``email_verified``.
    """

    def __init__(self, client_id: str):
        self._client_id = client_id
        self._request = google_requests.Request()

    def verify(self, raw_id_token: str) -> GoogleIdentity:
        try:
            claims = id_token.verify_oauth2_token(
                raw_id_token, self._request, self._client_id
            )
        except Exception as exc:  # ValueError on bad signature/aud/expiry, etc.
            raise AuthenticationError("invalid_google_token") from exc

        if claims.get("iss") not in _VALID_ISSUERS:
            raise AuthenticationError("invalid_google_token")
        if not claims.get("email_verified"):
            raise AuthenticationError("email_not_verified")

        return GoogleIdentity(
            sub=claims["sub"],
            email=claims["email"].strip().lower(),
            name=claims.get("name"),
        )
