from backend.agents.group3_logic.spec_check import (
    check_numeric,
    extract_spec,
    is_numeric_requirement,
)
from backend.agents.group3_logic.validator_agent import validate
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct
from backend.schemas.search import ProductSpecs, Requirement


def req(attr, op, value, unit=None):
    return Requirement(attribute=attr, operator=op, value=value, unit=unit)


def test_ram_e_ssd_numero_primeiro():
    t = 'Portátil HP 15.6" Intel Core i5 16GB RAM 512GB SSD'
    assert extract_spec(t, "ram_gb") == 16
    assert extract_spec(t, "storage_gb") == 512


def test_ram_e_ssd_etiqueta_primeiro():
    t = "Portátil Lenovo RAM 16GB SSD 512GB"
    assert extract_spec(t, "ram_gb") == 16
    assert extract_spec(t, "storage_gb") == 512


def test_vram_da_gpu():
    t = 'Placa Gráfica MSI GeForce RTX 5060 "Blackwell" Ventus 2X OC 8GB GDDR7'
    assert extract_spec(t, "vram_gb") == 8
    assert extract_spec(t, "ram_gb") is None


def test_tb_converte_para_gb():
    assert extract_spec("SSD Kingston NV3 NVMe 1TB", "storage_gb") == 1000


def test_varios_valores_e_ambiguo():
    assert extract_spec("Portátil 512GB SSD + 1TB HDD", "storage_gb") is None


def test_ecra_em_polegadas():
    assert extract_spec('Portátil HP 15.6" Intel', "screen_inches") == 15.6
    assert extract_spec("Monitor Gaming 27 polegadas", "screen_inches") == 27


def test_aspas_da_gpu_nao_sao_ecra():
    assert extract_spec('Placa Gráfica MSI RTX 5060 "Blackwell" 8GB GDDR7', "screen_inches") is None


def test_check_ok_fail_unknown():
    r = req("ram_gb", ">=", "16")
    assert check_numeric("Portátil 16GB RAM", r).status == "ok"
    bad = check_numeric("Portátil 8GB RAM", r)
    assert bad.status == "fail" and bad.found == 8
    assert check_numeric("Portátil sem especificações", r).status == "unknown"


def test_nome_alternativo_do_atributo():
    res = check_numeric("Portátil 8GB RAM", req("memory_gb", ">=", "16", "GB"))
    assert res is not None and res.status == "fail"


def test_requisitos_nao_numericos_sao_ignorados():
    assert not is_numeric_requirement(req("gpu", "contains", "RTX"))
    assert not is_numeric_requirement(req("cpu_cores", ">=", "6"))
    assert not is_numeric_requirement(req("ram_gb", "contains", "16"))


def _item(ext_id, title):
    p = ProductResult(store="pcdiga", external_id=ext_id, title=title,
                      url=f"https://www.pcdiga.com/{ext_id}", price=500)
    return RankedProduct(product=p, total_cost=500)


def test_validador_rejeita_so_quando_claramente_nao_cumpre():
    specs = ProductSpecs(category="laptop", requirements=[req("ram_gb", ">=", "16")])
    items = [
        _item("a", "Portátil X 8GB RAM 512GB SSD"),
        _item("b", "Portátil Y 16GB RAM 512GB SSD"),
        _item("c", "Portátil Z 512GB SSD"),
    ]
    ok, rejected = validate(items, None, None, specs)

    assert [r.product.external_id for r in rejected] == ["a"]
    assert rejected[0].reason.startswith("não cumpre requisito")
    assert "ram_gb" in rejected[0].reason
    assert [i.product.external_id for i in ok] == ["b", "c"]
    assert any(w.startswith("Não confirmado") for w in ok[1].warnings)