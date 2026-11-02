import os

import redis


class RedisSessions:
    def __init__(self, client, prefix: str = "zpd:session:") -> None:
        self.teachers = RedisTeacherTokens(client, prefix)
        self.students = RedisStudentTokens(client, prefix)


class RedisTeacherTokens:
    def __init__(self, client, prefix: str) -> None:
        self._client = client
        self._prefix = prefix + "teacher:"

    def add(self, token: str) -> None:
        self._client.set(self._key(token), "1")

    def discard(self, token: str) -> None:
        self._client.delete(self._key(token))

    def __contains__(self, token: object) -> bool:
        if not isinstance(token, str) or token == "":
            return False
        return bool(self._client.exists(self._key(token)))

    def _key(self, token: str) -> str:
        return self._prefix + token


class RedisStudentTokens:
    def __init__(self, client, prefix: str) -> None:
        self._client = client
        self._prefix = prefix + "student:"

    def __setitem__(self, token: str, account: str) -> None:
        self._client.set(self._key(token), account)

    def get(self, token: str, default=None):
        value = self._client.get(self._key(token))
        if value is None:
            return default
        return value

    def pop(self, token: str, default=None):
        value = self.get(token)
        if value is None:
            return default
        self._client.delete(self._key(token))
        return value

    def _key(self, token: str) -> str:
        return self._prefix + token


def redis_sessions() -> RedisSessions:
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    return RedisSessions(redis.Redis.from_url(url, decode_responses=True))
