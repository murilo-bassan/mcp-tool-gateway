import pytest

from gateway import masking


@pytest.mark.parametrize("raw, leaked, kept", [
    ("CPF 123.456.789-01 informado", "123.456.789", "89-01"),
    ("CNPJ 12.345.678/0001-95", "12.345.678", "-95"),
    ("contato: maria.silva@example.org", "maria.silva", "@example.org"),
    ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "abcdefghijklmnop", "Bearer ***"),
    ("key sk-or-v1-0123456789abcdefABCDEF", "0123456789abcdef", "sk-***"),
    ("ligue (67) 99876-5432", "99876-5432", "phone:***32"),
])
def test_mask_text_hides_and_keeps_suffix(raw, leaked, kept):
    masked = masking.mask_text(raw)
    assert leaked not in masked
    assert kept in masked


def test_secret_keys_are_blanked_whatever_the_value():
    masked = masking.mask({"user": "ana", "password": "hunter2", "nested": {"api_key": "x"}, "token": ""})
    assert masked == {"user": "ana", "password": "***", "nested": {"api_key": "***"}, "token": ""}


def test_mask_walks_lists():
    assert masking.mask(["a@b.co", 1, None]) == ["a***@b.co", 1, None]


def test_found_kinds():
    assert set(masking.found_kinds("x@y.com and 123.456.789-01")) >= {"email", "cpf"}
