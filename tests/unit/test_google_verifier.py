import pytest

import adapters.security.google_id_token_verifier as mod
from adapters.security.google_id_token_verifier import GoogleIdTokenVerifier
from domain.errors import AuthenticationError


def _patch(monkeypatch, claims=None, raise_exc=None):
    def fake_verify(token, request, client_id):
        if raise_exc is not None:
            raise raise_exc
        return claims
    monkeypatch.setattr(mod.id_token, "verify_oauth2_token", fake_verify)


def test_verify_returns_identity(monkeypatch):
    _patch(monkeypatch, claims={
        "iss": "https://accounts.google.com",
        "sub": "sub-1",
        "email": "USER@b.com",
        "email_verified": True,
        "name": "U",
    })
    identity = GoogleIdTokenVerifier("client-id").verify("tok")
    assert identity.sub == "sub-1"
    assert identity.email == "user@b.com"   # normalized
    assert identity.name == "U"


def test_verify_rejects_unverified_email(monkeypatch):
    _patch(monkeypatch, claims={
        "iss": "accounts.google.com",
        "sub": "s", "email": "u@b.com", "email_verified": False,
    })
    with pytest.raises(AuthenticationError):
        GoogleIdTokenVerifier("client-id").verify("tok")


def test_verify_rejects_bad_issuer(monkeypatch):
    _patch(monkeypatch, claims={
        "iss": "evil.example.com",
        "sub": "s", "email": "u@b.com", "email_verified": True,
    })
    with pytest.raises(AuthenticationError):
        GoogleIdTokenVerifier("client-id").verify("tok")


def test_verify_wraps_library_error(monkeypatch):
    # verify_oauth2_token raises ValueError on bad signature/aud/expiry.
    _patch(monkeypatch, raise_exc=ValueError("bad audience"))
    with pytest.raises(AuthenticationError):
        GoogleIdTokenVerifier("client-id").verify("tok")
