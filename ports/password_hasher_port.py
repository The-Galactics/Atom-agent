from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    # Contract for password hashing/verification. Implementations must use a
    # memory-hard algorithm (Argon2id) and embed the salt+params in the hash.
    @abstractmethod
    def hash(self, raw_password: str) -> str:
        """Returns a self-describing hash (algorithm + params + salt) for the password."""
        pass

    @abstractmethod
    def verify(self, raw_password: str, encoded: str) -> bool:
        """True iff the raw password matches the encoded hash."""
        pass

    @abstractmethod
    def needs_rehash(self, encoded: str) -> bool:
        """True when the hash was produced with weaker params and should be upgraded."""
        pass
