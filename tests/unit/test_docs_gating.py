from main import docs_settings


def test_docs_disabled_in_production():
    s = docs_settings("production")
    assert s["docs_url"] is None
    assert s["redoc_url"] is None
    assert s["openapi_url"] is None


def test_docs_disabled_for_prod_alias_and_case_insensitive():
    assert docs_settings("PROD")["openapi_url"] is None


def test_docs_enabled_in_development():
    s = docs_settings("development")
    assert s["docs_url"] == "/docs"
    assert s["openapi_url"] == "/openapi.json"
