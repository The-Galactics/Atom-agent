from domain.user.models import User
from domain.auth.models import TokenPair
from ports.user_repository_port import UserRepositoryPort
from ports.token_service_port import TokenServicePort
from ports.google_id_token_verifier_port import GoogleIdTokenVerifierPort


class AuthenticateWithGoogleUseCase:
    # Authenticates via a verified Google OIDC ID token: finds the linked account,
    # links Google to an existing email account, or provisions a new federated
    # user — then issues the same session token pair as a password login.
    def __init__(self, users: UserRepositoryPort, verifier: GoogleIdTokenVerifierPort,
                 tokens: TokenServicePort):
        self._users = users
        self._verifier = verifier
        self._tokens = tokens

    async def execute(self, raw_id_token: str) -> TokenPair:
        # Verifies signature, issuer, audience, expiry and email_verified.
        identity = self._verifier.verify(raw_id_token)
        user = await self._users.find_by_google_sub(identity.sub)
        if user is None:
            existing = await self._users.find_by_email(identity.email)
            if existing is not None:
                # Same verified email -> link Google to the existing account.
                user = await self._users.link_google(existing.id, identity.sub)
            else:
                user = await self._users.save(
                    User.federated(
                        email=identity.email,
                        google_sub=identity.sub,
                        display_name=identity.name,
                    )
                )
        return await self._tokens.issue_pair(user_id=user.id, email=user.email)
