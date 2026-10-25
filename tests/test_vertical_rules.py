from backend.agents.group3_logic.vertical_rules import matched_part_word


def test_peca_detetada():
    assert matched_part_word("Turbina Golf GTI 2.0 TFSI", "golf gti", "cars")
    assert matched_part_word("Faróis Golf 7 GTI", "golf gti", "cars")
    assert matched_part_word("Golf GTI para peças", "golf gti", "cars")


def test_carro_passa():
    assert matched_part_word("VW Golf GTI 2.0 TSI 220cv 2014", "golf gti", "cars") is None


def test_isento_se_pedido():
    assert matched_part_word("Jantes 18 Golf GTI", "jantes golf gti", "cars") is None


def test_vertical_sem_regras():
    assert matched_part_word("Turbina", "x", "tech") is None
    assert matched_part_word("Turbina", "x", None) is None

def test_pecas_no_inicio_do_titulo():
    assert matched_part_word("Motor VW Golf 6 Gti 2.0TFSI Ref: CCZ", "golf gti", "cars")
    assert matched_part_word("Turbo 2.0 TFSI IS20 Vw Golf GTI VII", "golf gti", "cars")
    assert matched_part_word("Veio de transmissão Traseiro 4Motion VW Golf R32", "golf gti", "cars")
    assert matched_part_word("Frente completa Volkswagen Golf MK7 Fase 1 GTi", "golf gti", "cars")
    assert matched_part_word("GRELHA FRONTAL GOLF 3 91-97 LOOK GTI PRETA", "golf gti", "cars")


def test_carro_com_turbo_ou_motor_no_meio_passa():
    assert matched_part_word("VW Golf GTI turbo 220cv", "golf gti", "cars") is None
    assert matched_part_word("VW Golf GTI motor 2.0 TSI revisto", "golf gti", "cars") is None

from backend.agents.group2_search.stores import STORES
from backend.agents.group3_logic.vertical_rules import split_non_vehicles
from backend.schemas.product import ProductResult
from backend.schemas.ranking import RankedProduct


def _item(store: str, title: str, price: float) -> RankedProduct:
    p = ProductResult(store=store, external_id="1", title=title, url="https://x.pt/1", price=price)
    return RankedProduct(product=p, shipping=None, taxes=0.0, total_cost=price, category=None, score=0.0, warnings=[])


def test_preco_minimo_so_em_loja_mista():
    items = [_item("olx", "Volkswagen Golf V GTI", 123.0), _item("standvirtual", "VW Golf GTI", 123.0)]
    keep, out = split_non_vehicles(items, "golf gti", "cars", STORES)
    assert [i.product.store for i in keep] == ["standvirtual"]
    assert "preço abaixo do mínimo" in out[0].reason


def test_preco_minimo_configuravel():
    items = [_item("olx", "VW Golf GTI", 500.0)]
    keep, _ = split_non_vehicles(items, "golf gti", "cars", STORES, min_price=300.0)
    assert len(keep) == 1


def test_moto_minimo_20_euros_em_loja_mista():
    items = [_item("olx", "Capacetes CMS lote", 1.0), _item("olx", "Capacete modular", 20.0),
             _item("motocard", "Capacete", 1.0)]
    keep, out = split_non_vehicles(items, "capacete modular", "moto", STORES)
    assert [i.product.title for i in keep] == ["Capacete modular", "Capacete"]
    assert "mínimo para moto (20 €)" in out[0].reason


def test_moto_acima_do_minimo_passa():
    items = [_item("olx", "Yamaha MT-07", 50.0)]
    keep, _ = split_non_vehicles(items, "yamaha mt-07", "moto", STORES)
    assert len(keep) == 1