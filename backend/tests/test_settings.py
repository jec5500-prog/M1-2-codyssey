import importlib

import pytest


def settings(env):
    try:
        return importlib.import_module('settings').load_settings(env)
    except ModuleNotFoundError:
        pytest.fail('Central environment configuration is missing')


def test_allowed_origins_are_trimmed_and_used():
    cfg = settings({'ALLOWED_ORIGINS': ' https://demo.vercel.app/,http://localhost:5500 '})
    assert cfg.allowed_origins == ['https://demo.vercel.app', 'http://localhost:5500']


def test_legacy_origins_work():
    assert settings({'CORS_ORIGINS': 'https://old.example'}).allowed_origins == ['https://old.example']


def test_conflicting_origin_names_fail_clearly():
    with pytest.raises(ValueError, match='ALLOWED_ORIGINS'):
        settings({'ALLOWED_ORIGINS': 'https://a.example', 'CORS_ORIGINS': 'https://b.example'})


@pytest.mark.parametrize('origin', ['*', 'https://example.com/path', 'javascript:alert(1)'])
def test_invalid_origins_are_rejected(origin):
    with pytest.raises(ValueError):
        settings({'ALLOWED_ORIGINS': origin})

