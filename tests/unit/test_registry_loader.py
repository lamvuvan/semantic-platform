from mcp.registry.loader import load_registry


def test_registry_loads_all_tools():
    tools = load_registry()
    names = [t.name for t in tools]
    assert "search_products" in names
    assert "recommend_toppings" in names
    assert "get_ontology_schema" in names
    assert all(callable(t.handler) for t in tools)


def test_pii_flag_set_for_customer_profile():
    tools = {t.name: t for t in load_registry()}
    assert tools["get_customer_profile"].pii is True
    assert tools["search_products"].pii is False
