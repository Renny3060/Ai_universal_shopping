import json
from types import SimpleNamespace as NS

from backend.agents.group2_search.plausibility import check_plausibility
from backend.services import store_health as h


def _setup(tmp_path, keys=("loja_a",)):
    auto = tmp_path / "stores_auto.json"
    auto.write_text(json.dumps({k: {} for k in keys}), encoding="utf-8")
    return tmp_path / "health.json", auto


def test_desativa_depois_de_falhas_seguidas(tmp_path):
    health, auto = _setup(tmp_path)
    for i in range(h.DISABLE_AFTER - 1):
        assert h.record("loja_a", 0, path=health, auto_path=auto) is False
    assert h.is_disabled("loja_a", health) is False
    assert h.record("loja_a", 0, error=True, path=health, auto_path=auto) is True
    assert h.is_disabled("loja_a", health) is True


def test_sucesso_zera_a_sequencia(tmp_path):
    health, auto = _setup(tmp_path)
    for _ in range(h.DISABLE_AFTER - 1):
        h.record("loja_a", 0, path=health, auto_path=auto)
    h.record("loja_a", 12, path=health, auto_path=auto)
    assert h.status(health)["loja_a"]["streak"] == 0
    for _ in range(h.DISABLE_AFTER - 1):
        h.record("loja_a", 0, path=health, auto_path=auto)
    assert h.is_disabled("loja_a", health) is False


def test_loja_manual_nao_e_acompanhada(tmp_path):
    health, auto = _setup(tmp_path)
    for _ in range(10):
        assert h.record("pcdiga", 0, error=True, path=health, auto_path=auto) is False
    assert h.is_disabled("pcdiga", health) is False
    assert "pcdiga" not in h.status(health)


def test_reativar(tmp_path):
    health, auto = _setup(tmp_path)
    for _ in range(h.DISABLE_AFTER):
        h.record("loja_a", 0, path=health, auto_path=auto)
    assert h.reenable("loja_a", health) is True
    assert h.is_disabled("loja_a", health) is False
    assert h.status(health)["loja_a"]["streak"] == 0
    assert h.reenable("nao_existe", health) is False


def _items(n=10, **over):
    base = dict(price=None, title=None, url=None)
    out = []
    for i in range(n):
        d = {"price": 20.0 + i, "title": f"Produto numero {i} completo", "url": f"https://www.loja.pt/p/{i}"}
        d.update({k: (v(i) if callable(v) else v) for k, v in over.items()})
        out.append(NS(**d))
    return out


def test_plausivel():
    ok, reasons = check_plausibility(_items(), "https://www.loja.pt")
    assert ok and reasons == []


def test_poucos_itens():
    ok, reasons = check_plausibility(_items(3), "https://www.loja.pt")
    assert not ok and "só 3 itens" in reasons[0]


def test_precos_todos_iguais():
    ok, reasons = check_plausibility(_items(price=9.9), "https://www.loja.pt")
    assert not ok and "preços quase todos iguais" in reasons


def test_titulos_e_links_repetidos():
    ok, reasons = check_plausibility(_items(title="Mesmo titulo", url="https://www.loja.pt/x"), "https://www.loja.pt")
    assert not ok
    assert "títulos repetidos" in reasons and "links repetidos" in reasons


def test_outro_dominio_e_extra_domains():
    items = _items(url=lambda i: f"https://outra.com/p/{i}")
    assert not check_plausibility(items, "https://www.loja.pt")[0]
    assert check_plausibility(items, "https://www.loja.pt", ["outra.com"])[0]


def test_precos_simbolicos():
    ok, reasons = check_plausibility(_items(price=lambda i: 0.5 + i * 0.01), "https://www.loja.pt")
    assert not ok and "muitos preços abaixo de 1 €" in reasons
