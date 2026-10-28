import pytest

from gateway import access
from gateway.errors import AuthFailed, PermissionDenied


@pytest.fixture
def seeded():
    access.seed_demo()


def test_password_hash_roundtrip_and_salt():
    a, b = access.hash_password("pw"), access.hash_password("pw")
    assert a != b
    assert access.verify_password("pw", a) and not access.verify_password("nope", a)


def test_login_and_session(seeded):
    token = access.login("analyst", "analyst")
    principal = access.from_session(token)
    assert principal.id == "analyst" and principal.role.name == "analyst"
    access.logout(token)
    with pytest.raises(AuthFailed):
        access.from_session(token)


def test_wrong_password_and_unknown_user_look_the_same(seeded):
    with pytest.raises(AuthFailed) as wrong:
        access.login("analyst", "x")
    with pytest.raises(AuthFailed) as unknown:
        access.login("ghost", "x")
    assert wrong.value.message == unknown.value.message


def test_role_globs(seeded):
    analyst = access.get_role("analyst")
    assert analyst.allows_tool("invoices.validate_tax_id")
    assert not analyst.allows_tool("registry.approve")
    assert access.get_role("admin").allows_tool("anything.at_all")


def test_consumer_api_key_is_shown_once_and_works(seeded):
    principal, key = access.create_consumer("grants-sync", "grants-bot")
    assert key.startswith("gw_")
    assert access.from_api_key(key).id == "grants-sync"
    with pytest.raises(AuthFailed):
        access.from_api_key(key + "x")


def test_blocking_kills_sessions(seeded):
    token = access.login("analyst", "analyst")
    access.set_status("analyst", "blocked")
    with pytest.raises(AuthFailed):
        access.from_session(token)
    with pytest.raises(AuthFailed):
        access.login("analyst", "analyst")


def test_admin_permission_check(seeded):
    auditor = access.get_principal("auditor")
    auditor.require("audit.read")
    with pytest.raises(PermissionDenied):
        auditor.require("registry.review")


def test_unknown_admin_perm_rejected():
    with pytest.raises(ValueError):
        access.upsert_role(access.Role(name="x", admin_perms=["root"]))
