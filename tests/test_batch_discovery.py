from backend.agents.group2_search.batch_discovery import (
    BLOCKED, NEEDS_CSS, NO_BOX, NO_TERM_IN_URL, OK_JSONLD, OPEN_ERROR,
    category_key, classify, drop_known, host_of, read_candidates, term_for,
)


def test_categoria_para_termo():
    assert term_for("Hardware e Informática", "PT") == "ssd 1tb"
    assert term_for("Motos e acessórios", "ES") == "casco moto"
    assert term_for("Carros e peças", "DE") == "reifen"
    assert term_for("Supermercado e saúde", "PT") == "champô"
    assert category_key("Livros e brinquedos") == "livros"
    assert category_key("Eletrónica de consumo") == "eletronica"


def test_pais_desconhecido_usa_portugues():
    assert term_for("Casa e jardim", "IT") == "aspirador"


def test_host_of():
    assert host_of("https://www.Loja.pt/abc") == "loja.pt"


def test_drop_known_remove_repetidas_e_conhecidas():
    rows = [{"url_inicial": "https://www.a.pt/"}, {"url_inicial": "https://a.pt/x"},
            {"url_inicial": "https://www.worten.pt/"}, {"url_inicial": "https://b.pt/"}]
    out = drop_known(rows, {"worten.pt"})
    assert [r["url_inicial"] for r in out] == ["https://www.a.pt/", "https://b.pt/"]


def test_classify():
    base = dict(opened=True, blocked=False, found_box=True, has_template=True, n_products=3)
    assert classify(**base) == OK_JSONLD
    assert classify(**{**base, "n_products": 0}) == NEEDS_CSS
    assert classify(**{**base, "has_template": False}) == NO_TERM_IN_URL
    assert classify(**{**base, "found_box": False}) == NO_BOX
    assert classify(**{**base, "blocked": True}) == BLOCKED
    assert classify(**{**base, "opened": False}) == OPEN_ERROR


def test_read_candidates_com_bom(tmp_path):
    f = tmp_path / "c.csv"
    f.write_text("nome,url_inicial,pais\nA,https://a.pt/,PT\nB,sem-url,PT\n", encoding="utf-8-sig")
    rows = read_candidates(f)
    assert len(rows) == 1 and rows[0]["nome"] == "A"