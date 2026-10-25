from backend.agents.group1_input.request_parser import extract_cpu, parse_request


def _attrs(req):
    return {(r.attribute, r.operator, r.value) for r in req.requirements}


def test_pedidos_simples_nao_mudam():
    assert parse_request("RTX 5060 até 650€").term == "rtx 5060"
    assert parse_request("RTX 5060 até 650€").max_budget == 650
    assert parse_request("audi tt até 15000€").term == "audi tt"
    assert parse_request("golf gti até 12000€").term == "golf gti"
    assert parse_request("lego ninjago até 30€").term == "lego ninjago"
    assert parse_request("capacete modular até 400€").term == "capacete modular"
    assert not parse_request("RTX 5060 até 650€").needs_llm_term


def test_capacidade_principal_fica_no_termo():
    assert parse_request("SSD 1TB até 100€").term == "ssd 1tb"
    assert parse_request("monitor 24 polegadas até 150€").term == "monitor 24 polegadas"
    assert parse_request("portátil com 16GB de RAM até 900€").term == "portátil 16gb"


def test_pedido_longo_e_completo():
    r = parse_request(
        "Quero um portátil gaming da Asus ou Lenovo com RTX 4060, 16GB de RAM, SSD 512GB e ecrã de "
        "15,6 polegadas, novo, entre 800 e 1200€, de preferência preto")
    assert r.term == "portátil gaming 16gb rtx 4060"
    assert (r.min_budget, r.max_budget) == (800, 1200)
    assert r.conditions == ["new"]
    assert r.brands == ["asus", "lenovo"]
    assert r.gpu == "rtx 4060"
    assert _attrs(r) == {("ram_gb", ">=", "16"), ("storage_gb", ">=", "512"),
                         ("screen_inches", "==", "15.6")}
    assert "preto" in r.extras and not r.needs_llm_term


def test_marca_unica_vai_ao_termo_e_varias_nao():
    assert parse_request("portátil asus até 900€").term == "portátil asus"
    assert "asus" not in parse_request("portátil asus ou lenovo até 900€").term


def test_estado():
    assert parse_request("telemóvel usado até 200€").conditions == ["used"]
    assert parse_request("portátil recondicionado até 500€").conditions == ["refurbished"]
    assert parse_request("portátil sem usados até 500€").conditions == ["new", "refurbished"]
    assert parse_request("portátil até 500€").conditions == []


def test_orcamento_minimo_e_intervalo():
    r = parse_request("portátil mais de 600€ até 1500€")
    assert (r.min_budget, r.max_budget) == (600, 1500)
    r = parse_request("monitor entre 150 e 250 euros")
    assert (r.min_budget, r.max_budget) == (150, 250)
    r = parse_request("portátil com mínimo 16GB de RAM")     # 16GB não é orçamento
    assert r.max_budget is None and r.min_budget is None


def test_processador_e_gpu():
    r = parse_request("portátil com intel core i7 e RTX 4070 Super até 1800€")
    assert r.cpu == "i7" and r.gpu == "rtx 4070 super"
    assert extract_cpu("Portátil Asus Ryzen 5 7535HS 16GB") == "ryzen 5"
    assert extract_cpu("Portátil HP Intel Core i5-1235U") == "i5"
    assert extract_cpu("Portátil sem processador indicado") is None


def test_etiquetas_nao_se_confundem():
    r = parse_request("portátil 16gb ram 512gb ssd até 800€")
    assert _attrs(r) == {("ram_gb", ">=", "16"), ("storage_gb", ">=", "512")}


def test_polegadas_numa_bicicleta_nao_sao_ecra():
    r = parse_request("bicicleta de montanha 29 polegadas até 500€")
    assert not r.requirements and "29" in r.term


def test_preferencias_nao_sao_obrigatorias():
    r = parse_request("portátil até 900€, de preferência da Samsung")
    assert r.brands == [] and r.soft_brands == ["samsung"]


def test_para_o_que_serve_nao_vai_ao_termo():
    assert parse_request("preciso de um portátil para estudar até 700€").term == "portátil"


def test_palavra_comum_nao_vira_marca():
    assert parse_request("tapete de yoga até 30€").brands == []
