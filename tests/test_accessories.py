from backend.agents.group3_logic.categories import classify_title
from backend.agents.group3_logic.validator_agent import validate
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct


def test_acessorios_pelo_inicio_do_titulo():
    assert classify_title("Carregador de Portátil Universal Nox NXPWR45NB 45W") == "accessory"
    assert classify_title('Suporte de Portátil Gembird NBS-D1-04 11" - 15.6"') == "accessory"


def test_portatil_real_continua_portatil():
    assert classify_title("Portátil Vanwin 15.6 Intel Pentium Gold 16GB RAM") == "laptop"
    assert classify_title("Portátil com mochila incluída 16GB") == "laptop"


def test_validador_rejeita_acessorio_quando_se_pede_portatil():
    p = ProductResult(store="pcdiga", external_id="1",
                      title="Carregador de Portátil Universal Nox 45W",
                      url="https://www.pcdiga.com/1", price=16.9)
    ok, rejected = validate([RankedProduct(product=p, total_cost=16.9)], "laptop", None, None)
    assert ok == []
    assert rejected[0].reason == "categoria diferente (accessory)"


def test_pedido_de_acessorio_nao_e_rejeitado_como_portatil():
    p = ProductResult(store="pcdiga", external_id="2", title="Carregador de Portátil HP 65W",
                      url="https://www.pcdiga.com/2", price=34.9)
    ok, _ = validate([RankedProduct(product=p, total_cost=34.9)], None, None, None)
    assert len(ok) == 1