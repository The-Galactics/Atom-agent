import asyncio

import pytest
from mongomock_motor import AsyncMongoMockClient

from adapters.user_store.mongo_user_repository import MongoUserRepository
from domain.errors import UserAlreadyExistsError
from domain.user.models import User


def _repo() -> MongoUserRepository:
    return MongoUserRepository(AsyncMongoMockClient(), "atom_test")


def test_save_and_find_by_email():
    repo = _repo()
    asyncio.run(repo.save(User.new("a@b.com", "hash:x", "Carlos")))
    found = asyncio.run(repo.find_by_email("a@b.com"))
    assert found is not None
    assert found.email == "a@b.com"
    assert found.password_hash == "hash:x"
    assert found.display_name == "Carlos"
    assert found.auth_providers == ["password"]


def test_find_by_id_and_google_sub():
    repo = _repo()
    saved = asyncio.run(repo.save(User.federated("g@b.com", "sub-1", "G")))
    assert asyncio.run(repo.find_by_id(saved.id)).email == "g@b.com"
    found = asyncio.run(repo.find_by_google_sub("sub-1"))
    assert found is not None and found.id == saved.id
    assert found.password_hash is None


def test_find_missing_returns_none():
    repo = _repo()
    assert asyncio.run(repo.find_by_email("nobody@b.com")) is None
    assert asyncio.run(repo.find_by_google_sub("nope")) is None


def test_link_google():
    repo = _repo()
    saved = asyncio.run(repo.save(User.new("a@b.com", "hash:x")))
    linked = asyncio.run(repo.link_google(saved.id, "sub-9"))
    assert linked.google_sub == "sub-9"
    assert "google" in linked.auth_providers
    assert "password" in linked.auth_providers


def test_update_password_hash_and_settings():
    repo = _repo()
    saved = asyncio.run(repo.save(User.new("a@b.com", "hash:x")))
    asyncio.run(repo.update_password_hash(saved.id, "hash:y"))
    assert asyncio.run(repo.find_by_id(saved.id)).password_hash == "hash:y"
    updated = asyncio.run(repo.update_settings(saved.id, {"theme": "dark"}))
    assert updated.settings == {"theme": "dark"}


def test_duplicate_email_raises():
    repo = _repo()
    asyncio.run(repo.ensure_indexes())
    asyncio.run(repo.save(User.new("a@b.com", "hash:x")))
    with pytest.raises(UserAlreadyExistsError):
        asyncio.run(repo.save(User.new("a@b.com", "hash:y")))
