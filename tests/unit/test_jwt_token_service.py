import asyncio

from adapters.security.jwt_token_service import JwtTokenService
from adapters.security.in_memory_refresh_token_store import InMemoryRefreshTokenStore
from domain.auth.models import Principal


def _service(access_ttl: int = 900) -> JwtTokenService:
    return JwtTokenService(
        InMemoryRefreshTokenStore(),
        signing_key="test-secret",
        algorithm="HS256",
        access_ttl_seconds=access_ttl,
        refresh_ttl_seconds=3600,
        issuer="atom-agent",
    )


def test_issue_and_verify_access():
    svc = _service()
    pair = asyncio.run(svc.issue_pair("user-1", "u@b.com"))
    principal = svc.verify_access(pair.access_token)
    assert isinstance(principal, Principal)
    assert principal.user_id == "user-1"
    assert principal.email == "u@b.com"
    assert pair.expires_in == 900


def test_verify_rejects_tampered_token():
    svc = _service()
    pair = asyncio.run(svc.issue_pair("user-1"))
    assert svc.verify_access(pair.access_token + "x") is None


def test_verify_rejects_wrong_secret():
    svc = _service()
    pair = asyncio.run(svc.issue_pair("user-1"))
    other = JwtTokenService(InMemoryRefreshTokenStore(), signing_key="different-secret")
    assert other.verify_access(pair.access_token) is None


def test_verify_rejects_expired():
    svc = _service(access_ttl=-1)  # exp in the past
    pair = asyncio.run(svc.issue_pair("user-1"))
    assert svc.verify_access(pair.access_token) is None


def test_verify_rejects_refresh_token_as_access():
    # The refresh token is opaque (not a JWT); verify_access must reject it.
    svc = _service()
    pair = asyncio.run(svc.issue_pair("user-1"))
    assert svc.verify_access(pair.refresh_token) is None


def test_rotate_is_single_use():
    svc = _service()
    pair = asyncio.run(svc.issue_pair("user-1"))
    rotated = asyncio.run(svc.rotate(pair.refresh_token))
    assert rotated is not None
    assert rotated.refresh_token != pair.refresh_token
    assert rotated.user_id == "user-1"
    # The old refresh token is now invalid.
    assert asyncio.run(svc.rotate(pair.refresh_token)) is None


def test_revoke_invalidates_refresh():
    svc = _service()
    pair = asyncio.run(svc.issue_pair("user-1"))
    asyncio.run(svc.revoke(pair.refresh_token))
    assert asyncio.run(svc.rotate(pair.refresh_token)) is None


def _rsa_keypair() -> tuple[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def test_rs256_issue_and_verify():
    private_pem, public_pem = _rsa_keypair()
    svc = JwtTokenService(
        InMemoryRefreshTokenStore(),
        signing_key=private_pem,
        verifying_key=public_pem,
        algorithm="RS256",
        issuer="atom-agent",
    )
    pair = asyncio.run(svc.issue_pair("user-1", "u@b.com"))
    principal = svc.verify_access(pair.access_token)
    assert isinstance(principal, Principal)
    assert principal.user_id == "user-1"
    assert principal.email == "u@b.com"


def test_rs256_rejects_token_signed_by_other_key():
    priv_a, _ = _rsa_keypair()
    _, pub_b = _rsa_keypair()
    issuer = JwtTokenService(
        InMemoryRefreshTokenStore(), signing_key=priv_a,
        verifying_key=pub_b, algorithm="RS256",
    )
    # Sign with key A but verify against the unrelated public key B → rejected.
    pair = asyncio.run(issuer.issue_pair("user-1"))
    assert issuer.verify_access(pair.access_token) is None
