from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exceptions

from ports.password_hasher_port import PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    """Argon2id password hasher (memory-hard).

    Defaults follow OWASP guidance; tune ``memory_cost``/``time_cost`` to the host.
    The hash is self-describing (algorithm + params + random salt embedded), so
    ``verify`` and ``needs_rehash`` need no external state.
    """

    def __init__(self, time_cost: int = 3, memory_cost: int = 65536,
                 parallelism: int = 4, hash_len: int = 32, salt_len: int = 16):
        self._ph = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    def hash(self, raw_password: str) -> str:
        return self._ph.hash(raw_password)

    def verify(self, raw_password: str, encoded: str) -> bool:
        try:
            return self._ph.verify(encoded, raw_password)
        except (argon2_exceptions.VerifyMismatchError,
                argon2_exceptions.InvalidHashError,
                argon2_exceptions.VerificationError):
            return False

    def needs_rehash(self, encoded: str) -> bool:
        try:
            return self._ph.check_needs_rehash(encoded)
        except argon2_exceptions.InvalidHashError:
            # An unparseable hash should be replaced on next successful login.
            return True
