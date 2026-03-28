import os


def env(key: str, default=None):
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    return int(value) if value is not None else default


def env_csv(key: str, default=None):
    value = os.getenv(key)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]
