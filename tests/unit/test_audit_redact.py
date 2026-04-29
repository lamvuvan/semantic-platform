from mcp.audit.log import _redact


def test_redact_removes_pii_keys():
    out = _redact({"customer_id": "C1", "phone": "0900", "email": "a@b", "raw_pii": "x"})
    assert out["phone"] == "***"
    assert out["email"] == "***"
    assert out["raw_pii"] == "***"
    assert out["customer_id"] == "C1"
