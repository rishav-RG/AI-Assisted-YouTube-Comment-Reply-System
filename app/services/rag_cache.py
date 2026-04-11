import hashlib
import json
from typing import Any, Optional

from redis import Redis

from config import REDIS_CACHE_TTL_SECONDS, REDIS_URL


class RAGCache:
    def __init__(self) -> None:
        self.enabled = bool(REDIS_URL)
        self.ttl = REDIS_CACHE_TTL_SECONDS
        self._client: Optional[Redis] = None
        if self.enabled:
            self._client = Redis.from_url(REDIS_URL, decode_responses=True)

    @staticmethod
    def stable_hash(payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _key(self, scope: str, key: str) -> str:
        return f"rag:{scope}:{key}"

    def get_json(self, scope: str, key: str) -> Optional[dict]:
        if not self._client:
            return None
        value = self._client.get(self._key(scope, key))
        if not value:
            return None
        return json.loads(value)

    def set_json(self, scope: str, key: str, value: dict, ttl: Optional[int] = None) -> None:
        if not self._client:
            return
        self._client.set(
            self._key(scope, key),
            json.dumps(value, ensure_ascii=True),
            ex=ttl or self.ttl,
        )

    def delete_prefix(self, scope: str, starts_with: str) -> int:
        if not self._client:
            return 0

        cursor = 0
        deleted = 0
        pattern = self._key(scope, f"{starts_with}*")
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                deleted += self._client.delete(*keys)
            if cursor == 0:
                break
        return deleted
