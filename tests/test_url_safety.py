from backend.agents.group3_logic.pipeline import run_group3
from backend.schemas.product import ProductResult
from backend.services.url_safety import check_url

BASE = "https://www.pcdiga.com"


def test_mesmo_dominio_ok():
    assert check_url("https://www.pcdiga.com/placa/123", BASE).ok


def test_http_rejeitado():
    r = check_url("http://www.pcdiga.com/placa/123", BASE)
    assert not r.ok and "HTTPS" in r.problems[0]


def test_dominio_de_outra_loja():
    assert not check_url("https://www.worten.pt/produtos/x", BASE).ok


def test_dominio_parecido_rejeitado():
    assert not check_url("https://www.pcdiga.com.evil.com/x", BASE).ok
    assert not check_url("https://pcdiga-promo.example/x", BASE).ok


def test_truque_do_arroba():
    r = check_url("https://www.pcdiga.com@evil.com/p", BASE)
    assert not r.ok
    assert any("@" in p for p in r.problems)


def test_subdominio_ok():
    assert check_url("https://shop.pcdiga.com/x", BASE).ok


def test_sem_www_ok():
    assert check_url("https://pcdiga.com/x", BASE).ok


def test_ip_rejeitado():
    assert not check_url("https://192.168.1.10/x", BASE).ok


def test_porta_invulgar():
    assert not check_url("https://www.pcdiga.com:8443/x", BASE).ok


def test_sem_base_url_valida_so_o_resto():
    assert check_url("https://qualquer.pt/x").ok
    assert not check_url("http://qualquer.pt/x").ok


def test_url_vazio():
    assert not check_url("", BASE).ok


def test_pipeline_rejeita_url_suspeito():
    good = ProductResult(store="pcdiga", external_id="1", title="Placa Gráfica RTX 5060",
                         url="https://www.pcdiga.com/p/1", price=450)
    bad = ProductResult(store="pcdiga", external_id="2", title="Placa Gráfica RTX 5060",
                        url="https://pcdiga-promo.example/p/2", price=400)
    ranked, rejected, _ = run_group3([good, bad], wanted_text="RTX 5060")
    assert [r.product.external_id for r in ranked] == ["1"]
    assert len(rejected) == 1
    assert rejected[0].reason.startswith("URL suspeito")