from pymongo.errors import DuplicateKeyError

from domain.errors import UserAlreadyExistsError
from domain.user.models import User
from ports.user_repository_port import UserRepositoryPort


class MongoUserRepository(UserRepositoryPort):
    """User store backed by MongoDB (async, via motor).

    Uniqueness of ``email`` (and ``google_sub`` when present) is enforced by the
    DB indexes created in ``ensure_indexes`` — the real safety net against a
    double-registration race, not just the use-case check.
    """

    def __init__(self, client, db_name: str, collection: str = "users"):
        self._col = client[db_name][collection]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("email", unique=True)
        # partialFilterExpression (not sparse) so multiple email-only users —
        # which have no google_sub — don't collide on a present null key.
        await self._col.create_index(
            "google_sub",
            unique=True,
            partialFilterExpression={"google_sub": {"$type": "string"}},
        )

    @staticmethod
    def _to_doc(user: User) -> dict:
        doc = {
            "_id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "auth_providers": user.auth_providers,
            "display_name": user.display_name,
            "active": user.active,
            "settings": user.settings,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        # Only persist google_sub when set, so the partial unique index ignores
        # email-only accounts entirely.
        if user.google_sub is not None:
            doc["google_sub"] = user.google_sub
        return doc

    @staticmethod
    def _to_domain(doc: dict) -> User:
        return User(
            id=doc["_id"],
            email=doc["email"],
            password_hash=doc.get("password_hash"),
            google_sub=doc.get("google_sub"),
            auth_providers=doc.get("auth_providers", []),
            display_name=doc.get("display_name"),
            active=doc.get("active", True),
            settings=doc.get("settings", {}),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

    async def find_by_email(self, email: str) -> User | None:
        doc = await self._col.find_one({"email": email})
        return self._to_domain(doc) if doc else None

    async def find_by_id(self, user_id: str) -> User | None:
        doc = await self._col.find_one({"_id": user_id})
        return self._to_domain(doc) if doc else None

    async def find_by_google_sub(self, google_sub: str) -> User | None:
        doc = await self._col.find_one({"google_sub": google_sub})
        return self._to_domain(doc) if doc else None

    async def save(self, user: User) -> User:
        try:
            await self._col.insert_one(self._to_doc(user))
        except DuplicateKeyError as exc:
            raise UserAlreadyExistsError() from exc
        return user

    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        await self._col.update_one(
            {"_id": user_id}, {"$set": {"password_hash": password_hash}}
        )

    async def update_settings(self, user_id: str, settings: dict) -> User:
        await self._col.update_one({"_id": user_id}, {"$set": {"settings": settings}})
        return await self.find_by_id(user_id)

    async def link_google(self, user_id: str, google_sub: str) -> User:
        await self._col.update_one(
            {"_id": user_id},
            {
                "$set": {"google_sub": google_sub},
                "$addToSet": {"auth_providers": "google"},
            },
        )
        return await self.find_by_id(user_id)
