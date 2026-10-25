from backend.services.store_overview import store_overview

STORES = {
    "a": {"verticals": ["tech"]},
    "b": {"verticals": ["tech", "general"]},
    "c": {},
    "d": {"verticals": ["moto"]},
}


def test_estados_e_ultima_pesquisa():
    rows = store_overview(
        STORES, excluded=["b"], last_counts={"a": 12}, last_errors={"c": "NR", "d": "Tempo esgotado"},
        no_results_msg="NR", auto_keys={"c"}, health={"c": {"disabled": True}},
    )
    by = {r["Loja"]: r for r in rows}
    assert by["a"]["Estado"] == "Ativa" and by["a"]["Última pesquisa"] == "12 itens"
    assert by["b"]["Estado"] == "Excluída por ti" and by["b"]["Tipo"] == "tech/general"
    assert by["b"]["Última pesquisa"] == "não pesquisada"
    assert by["c"]["Estado"].startswith("Desativada") and by["c"]["Origem"] == "automática"
    assert by["c"]["Tipo"] == "todas" and by["c"]["Última pesquisa"] == "sem resultados"
    assert by["d"]["Última pesquisa"].startswith("erro: Tempo")
    assert len(rows) == 4
