from backend.agents.group2_search.stores import STORES
from backend.services.url_safety import check_url


def test_extra_domains():
    url = "https://www.standvirtual.com/carros/anuncio/x.html"
    assert not check_url(url, "https://www.olx.pt").ok
    assert check_url(url, "https://www.olx.pt", ["standvirtual.com"]).ok


def test_todas_as_lojas_tem_verticals():
    for name, cfg in STORES.items():
        assert cfg.get("verticals"), name


def test_carros_sem_aliexpress():
    cars = [n for n, c in STORES.items() if "cars" in c["verticals"]]
    assert "standvirtual" in cars and "olx" in cars
    assert "aliexpress" not in cars and "amazon_es" not in cars