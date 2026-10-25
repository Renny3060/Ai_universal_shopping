from backend.utils.parsing import parse_price


def test_formats():
    assert parse_price("1 299,99 €") == 1299.99
    assert parse_price("1.299,00€") == 1299.0
    assert parse_price("49,9€") == 49.9
    assert parse_price("€1,299.50") == 1299.5
    assert parse_price("1.299 €") == 1299.0


def test_invalid():
    assert parse_price("sem preço") is None
    assert parse_price("") is None