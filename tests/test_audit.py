from gateway import audit, store


def _emit(n: int) -> None:
    for i in range(n):
        audit.record(audit.Event(kind="tool_call", actor="ana", tool=f"t{i % 2}", outcome="ok",
                                 duration_ms=10 * i, payload={"i": i}))


def test_chain_verifies_when_untouched():
    _emit(5)
    report = audit.verify_chain()
    assert report.ok and report.checked == 5 and report.head_hash


def test_editing_a_past_row_is_detected():
    _emit(5)
    with store.transaction() as conn:
        conn.execute("UPDATE events SET payload = '{\"i\": 999}' WHERE seq = 3")
    report = audit.verify_chain()
    assert not report.ok
    assert report.first_broken_seq == 3


def test_deleting_a_row_is_detected():
    _emit(4)
    with store.transaction() as conn:
        conn.execute("DELETE FROM events WHERE seq = 2")
    assert audit.verify_chain().first_broken_seq == 3


def test_payload_is_masked_before_storage():
    audit.record(audit.Event(kind="tool_call", payload={"cpf": "123.456.789-01", "password": "p"}))
    stored = audit.search(kind="tool_call")[0]
    assert "123.456.789" not in str(stored.payload)
    assert stored.payload["password"] == "***"


def test_stats_aggregates_per_tool():
    _emit(6)
    audit.record(audit.Event(kind="tool_call", tool="t0", outcome="tool_failed", duration_ms=5))
    stats = {row["tool"]: row for row in audit.stats()["tools"]}
    assert stats["t0"]["calls"] == 4 and stats["t0"]["errors"] == 1
    assert stats["t1"]["error_rate"] == 0


def test_correlated_returns_in_order():
    for i in range(3):
        audit.record(audit.Event(kind="tool_call", correlation="c-1", payload={"i": i}))
    assert [e.payload["i"] for e in audit.correlated("c-1")] == [0, 1, 2]
