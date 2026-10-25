"""Validated configuration; platform values take precedence over local .env."""
import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    allowed_origins: list[str]
    openai_model: str = 'gpt-4o-mini'
    chat_deadline_seconds: int = 90
    openai_timeout_seconds: int = 20
    max_completion_tokens: int = 600
    max_tool_rounds: int = 3
    max_tools_per_round: int = 3
    chat_requests_per_minute: int = 6


def _origins(raw: str) -> list[str]:
    result = []
    for value in raw.split(','):
        value = value.strip().rstrip('/')
        if not value:
            continue
        parsed = urlsplit(value)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.path or parsed.query or parsed.fragment or parsed.username
                or parsed.password or parsed.netloc != parsed.hostname + (f':{parsed.port}' if parsed.port else '')):
            raise ValueError('ALLOWED_ORIGINS must contain exact HTTP(S) origins')
        if value not in result:
            result.append(value)
    return result


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    primary = env.get('ALLOWED_ORIGINS', '').strip()
    legacy = env.get('CORS_ORIGINS', '').strip()
    if primary and legacy and set(_origins(primary)) != set(_origins(legacy)):
        raise ValueError('ALLOWED_ORIGINS and CORS_ORIGINS conflict')
    origins = _origins(primary or legacy or 'http://localhost:5500,http://127.0.0.1:5500')
    if not origins:
        raise ValueError('ALLOWED_ORIGINS must not be empty')
    return Settings(allowed_origins=origins, openai_model=env.get('OPENAI_MODEL', 'gpt-4o-mini'))
