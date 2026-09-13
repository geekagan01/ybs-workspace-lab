import json
from urllib.parse import parse_qs, urlsplit

import pytest

from ybs_cli.redaction import redact


def test_redact_nested_values_headers_and_query_strings() -> None:
    value = {
        "Authorization": "Bearer top-secret",
        "url": "https://example.test/run?token=abc123&safe=yes",
        "nested": {"api_key": "abc123", "message": "use abc123"},
    }

    result = redact(value, secrets=["abc123", "top-secret"])

    rendered = json.dumps(result)
    assert "abc123" not in rendered
    assert "top-secret" not in rendered
    assert "***REDACTED***" in rendered


@pytest.mark.parametrize(
    "key",
    ["authorization", "AUTHORIZATION", "token", "secret", "password", "api_key", "API-key"],
)
def test_redact_replaces_whole_value_for_sensitive_full_keys(key: str) -> None:
    value = {key: {"nested": "not retained"}}

    assert redact(value) == {key: "***REDACTED***"}


def test_redact_does_not_classify_compound_nonsensitive_key() -> None:
    value = {"x-authorization-note": "visible"}

    assert redact(value) == value


def test_redact_preserves_list_and_tuple_shape_and_non_string_scalars() -> None:
    marker = object()
    value = ["prefix needle suffix", (42, None, marker)]

    result = redact(value, secrets=["needle", ""])

    assert result == ["prefix ***REDACTED*** suffix", (42, None, marker)]
    assert isinstance(result, list)
    assert isinstance(result[1], tuple)


def test_redact_replaces_explicit_secrets_in_mapping_keys() -> None:
    value = {"label-needle": "visible"}

    assert redact(value, secrets=["needle"]) == {"label-***REDACTED***": "visible"}


def test_redact_parses_and_rebuilds_url_query_values() -> None:
    value = "https://example.test/run?Api-Key=visible&safe=prefix-needle#result"

    result = redact(value, secrets=["needle"])

    assert isinstance(result, str)
    parsed = urlsplit(result)
    assert parsed.fragment == "result"
    assert parse_qs(parsed.query) == {
        "Api-Key": ["***REDACTED***"],
        "safe": ["prefix-***REDACTED***"],
    }
    assert "visible" not in result
    assert "needle" not in result


def test_redact_explicit_secret_in_malformed_url_like_text() -> None:
    value = "http://[broken/needle"

    assert redact(value, secrets=["needle"]) == "http://[broken/***REDACTED***"


@pytest.mark.parametrize(
    "secrets",
    [
        ["top", "top-secret"],
        ["secret", "top-secret"],
        ["top", "top-secret", "top-secret"],
    ],
)
def test_redact_prefers_longest_overlapping_explicit_secret(secrets: list[str]) -> None:
    assert redact("Bearer top-secret", secrets=secrets) == "Bearer ***REDACTED***"
