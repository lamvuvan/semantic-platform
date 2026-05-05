from mcp_server.middleware.audit import _redact


def test_redact_pii_keys():
    out = _redact({"customer_id": "C1", "phone": "09", "email": "a@b", "token": "abc"})
    assert out["phone"] == "***"
    assert out["email"] == "***"
    assert out["token"] == "***"
    assert out["customer_id"] == "C1"
