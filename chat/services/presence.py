from django.core.cache import cache


def _connection_count_key(user_id: int) -> str:
    return f"chat:presence:connections:{user_id}"


def mark_user_connected(user_id: int) -> None:
    key = _connection_count_key(user_id)
    current = cache.get(key, 0) or 0
    cache.set(key, int(current) + 1, timeout=None)


def mark_user_disconnected(user_id: int) -> None:
    key = _connection_count_key(user_id)
    current = cache.get(key, 0) or 0
    next_value = max(int(current) - 1, 0)
    cache.set(key, next_value, timeout=None)


def is_user_online(user_id: int) -> bool:
    key = _connection_count_key(user_id)
    count = cache.get(key, 0) or 0
    return int(count) > 0
