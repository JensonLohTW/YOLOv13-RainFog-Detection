import json
from typing import Optional

import redis
from django.conf import settings


class RedisCache:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
        return self._client

    def get_json(self, key: str):
        try:
            raw = self._get_client().get(key)
            return json.loads(raw) if raw else None
        except redis.RedisError:
            return None

    def set_json(self, key: str, value, ttl: Optional[int] = None) -> None:  # noqa: ANN001
        try:
            self._get_client().set(key, json.dumps(value, ensure_ascii=False), ex=ttl or settings.REDIS_CACHE_TTL)
        except redis.RedisError:
            return None

    def delete(self, key: str) -> None:
        try:
            self._get_client().delete(key)
        except redis.RedisError:
            return None


cache = RedisCache()
