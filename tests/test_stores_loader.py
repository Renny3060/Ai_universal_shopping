from backend.agents.group2_search.stores import STORES

AUTO = ["motoscoot", "custojusto", "prof", "bertrand", "vertbaudet", "almedina"]


def test_lojas_automaticas_carregadas():
    for key in AUTO:
        assert key in STORES, key
        cfg = STORES[key]
        assert "{q}" in cfg["search_url"]
        assert cfg["base_url"].startswith("https://")
        assert cfg.get("verticals")


def test_lojas_a_mao_nao_sao_substituidas():
    assert STORES["pcdiga"]["card"] == "div.product-list div.bg-background-off"
    assert STORES["olx"]["private_listings"] is True


def test_total_de_lojas():
    assert len(STORES) >= 16
