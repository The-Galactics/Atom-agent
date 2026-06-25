from adapters.security.argon2_password_hasher import Argon2PasswordHasher


def _fast_hasher() -> Argon2PasswordHasher:
    # Low cost params so the unit tests stay fast (production params live in the
    # adapter's defaults / config).
    return Argon2PasswordHasher(time_cost=1, memory_cost=512, parallelism=1)


def test_hash_verify_roundtrip():
    hasher = _fast_hasher()
    encoded = hasher.hash("correct horse battery")
    assert hasher.verify("correct horse battery", encoded) is True


def test_verify_rejects_wrong_password():
    hasher = _fast_hasher()
    encoded = hasher.hash("secret123")
    assert hasher.verify("secret124", encoded) is False


def test_hash_is_argon2id_and_not_plaintext():
    hasher = _fast_hasher()
    encoded = hasher.hash("my-password")
    assert encoded.startswith("$argon2id$")
    assert "my-password" not in encoded


def test_hash_is_salted_unique():
    hasher = _fast_hasher()
    assert hasher.hash("same") != hasher.hash("same")  # random salt per hash


def test_verify_invalid_hash_returns_false():
    hasher = _fast_hasher()
    assert hasher.verify("whatever", "not-a-valid-hash") is False


def test_needs_rehash_false_for_matching_params():
    hasher = _fast_hasher()
    encoded = hasher.hash("pw")
    assert hasher.needs_rehash(encoded) is False
