"""Redis-backed login rate limiting."""

import hashlib

import redis
from fastapi import HTTPException, Request

from app.core.config import settings


def _client():
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


def _key(email: str, client_ip: str) -> str:
    normalized_email = email.strip().lower()
    identity = f'{client_ip}:{normalized_email}'
    digest = hashlib.sha256(identity.encode()).hexdigest()
    return f'aiml02:login:{digest}'


def _redis_error(exc: Exception):
    raise HTTPException(
        status_code=503,
        detail='Authentication service temporarily unavailable. Please try again shortly.',
        headers={'Retry-After': '5'},
    ) from exc


def check_login_limit(email: str, request: Request) -> str:
    """Reject login when the configured failed-attempt limit is reached."""

    client_ip = request.client.host if request.client else 'unknown'
    key = _key(email, client_ip)

    try:
        client = _client()

        attempts = int(client.get(key) or 0)

        if attempts >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
            ttl = max(client.ttl(key), 1)

            raise HTTPException(
                status_code=429,
                detail='Too many failed login attempts. Please try again later.',
                headers={'Retry-After': str(ttl)},
            )

        return key

    except HTTPException:
        raise
    except redis.RedisError as exc:
        _redis_error(exc)


def record_failed_login(key: str) -> int:
    """Atomically increment failed attempts and set the expiry."""

    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """

    try:
        client = _client()

        return int(
            client.eval(
                script,
                1,
                key,
                settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            )
        )

    except redis.RedisError as exc:
        _redis_error(exc)


def reset_login_limit(key: str) -> None:
    """Clear failed attempts after successful authentication."""

    try:
        _client().delete(key)

    except redis.RedisError as exc:
        _redis_error(exc)