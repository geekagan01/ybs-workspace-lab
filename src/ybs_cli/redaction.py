import re
from collections.abc import Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_REDACTED = "***REDACTED***"
_SENSITIVE_KEY = re.compile(r"(?:authorization|token|secret|password|api[_-]?key)", re.I)


def redact(value: object, secrets: Sequence[str] = ()) -> object:
    """Return a safely renderable form of a potentially sensitive value."""
    explicit_secrets = tuple(secret for secret in secrets if secret)
    return _redact_value(value, explicit_secrets)


def _redact_value(value: object, secrets: tuple[str, ...]) -> object:
    if isinstance(value, Mapping):
        redacted_mapping: dict[object, object] = {}
        for key, item in value.items():
            redacted_key = _redact_text(key, secrets) if isinstance(key, str) else key
            redacted_mapping[redacted_key] = (
                _REDACTED
                if isinstance(key, str) and _SENSITIVE_KEY.fullmatch(key)
                else _redact_value(item, secrets)
            )
        return redacted_mapping
    if isinstance(value, list):
        return [_redact_value(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, secrets) for item in value)
    if isinstance(value, str):
        return _redact_text(value, secrets)
    return value


def _redact_text(value: str, secrets: tuple[str, ...]) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return _replace_explicit_secrets(value, secrets)
    if not parsed.query:
        return _replace_explicit_secrets(value, secrets)

    query_items = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        redacted_key = _replace_explicit_secrets(key, secrets)
        redacted_item = (
            _REDACTED if _SENSITIVE_KEY.fullmatch(key) else _replace_explicit_secrets(item, secrets)
        )
        query_items.append((redacted_key, redacted_item))

    return urlunsplit(
        (
            _replace_explicit_secrets(parsed.scheme, secrets),
            _replace_explicit_secrets(parsed.netloc, secrets),
            _replace_explicit_secrets(parsed.path, secrets),
            urlencode(query_items),
            _replace_explicit_secrets(parsed.fragment, secrets),
        )
    )


def _replace_explicit_secrets(value: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        value = value.replace(secret, _REDACTED)
    return value
