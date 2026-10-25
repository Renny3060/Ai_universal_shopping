import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Permite importar "backend" ao correr: streamlit run frontend\app.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# O Playwright precisa deste tipo de event loop no Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import pandas as pd
import streamlit as st

from backend.agents.group1_input.pipeline import LAST_RUN as G1_RUN, run_group1
from backend.agents.group1_input.request_parser import describe, finalize_request, parse_request
from backend.agents.group1_input.profile_agent import load_user_context
from backend.agents.group2_search.stores import STORES
from backend.agents.group3_logic.categories import category_hint, infer_wanted_category
from backend.agents.group3_logic.category_llm import LAST_RUN, classify_titles
from backend.agents.group3_logic.near_misses import MIN_RESULTS, near_misses
from backend.agents.group3_logic.pipeline import run_group3
from backend.agents.group3_logic.sellers import is_external_seller
from backend.db.database import SessionLocal
from backend.db.models import UserProfile
from backend.services.alerts import check_alerts
from backend.services.store_overview import store_overview
from backend.services.favorites import (
    FavoriteError,
    add_favorite,
    list_favorites,
    list_folders,
    remove_favorite,
    set_target_price,
)
from backend.utils.query_cleaning import clean_search_term
from backend.agents.group3_logic.vertical_rules import detect_vertical
from backend.agents.group2_search.aggregator import NO_RESULTS, search_all

st.set_page_config(page_title="Universal AI Shopping", page_icon="🛒", layout="wide")


def save_excluded(excluded: list[str]) -> None:
    with SessionLocal() as db:
        profile = db.query(UserProfile).first()
        if profile:
            profile.excluded_stores = list(excluded)
            db.commit()


# ---------- Barra lateral: perfil e filtros ----------
user = load_user_context()
with st.sidebar:
    st.header("Perfil")
    st.write(f"País: **{user.country}** · Moeda: **{user.currency}**")
    excluded = st.multiselect(
        f"Lojas a excluir ({len(STORES)} disponíveis)",
        list(STORES),
        format_func=lambda s: f"{s} · {'/'.join(STORES[s].get('verticals') or ['todas'])}",
        default=[s for s in user.excluded_stores if s in STORES],
    )
    if set(excluded) != set(user.excluded_stores):
        save_excluded(excluded)

    st.header("Filtros")
    sort_label = st.radio("Ordenar por", ["Melhor valor", "Menor custo total"])
    conditions = st.multiselect(
        "Estado do artigo",
        ["new", "refurbished", "used"],
        default=["new", "refurbished", "used"],
    )
    only_own = st.checkbox("Só vendidos pela própria loja", value=False)
    use_cache = st.checkbox("Usar cache (mais rápido)", value=True)
    vertical_choice = st.selectbox(
        "Tipo de pesquisa",
        ["Automático", "Todas as lojas", "tech", "general", "cars", "moto"],
    )
    store_box = st.container()      # preenchida no fim do script, com o resultado da pesquisa atual

st.title("🛒 Universal AI Shopping")
tab_search, tab_fav = st.tabs(["Pesquisa", "Favoritos"])

# =====================================================================
# Separador: Pesquisa
# =====================================================================
with tab_search:
    text = st.text_area(
        "O que procuras?",
        placeholder="Ex.: RTX 5060 até 500€",
        height=90,
    )

    if st.button("Pesquisar", type="primary") and text.strip():
        with st.spinner("A pesquisar e a validar os resultados... pode demorar alguns minutos (máx. 10). Por favor, aguarda."):
            with ThreadPoolExecutor(max_workers=1) as pool:
                g1_future = pool.submit(run_group1, text)     # LLM em paralelo com o scraping
                req = parse_request(text)     # regras instantâneas: termo, orçamento, estado, marca...
                term = req.term
                eq = None
                if req.needs_llm_term:
                    eq = g1_future.result()
                    term = clean_search_term(" ".join(eq.query.keywords[:3])) or term
                hint = category_hint(term, text)
                if vertical_choice == "Automático":
                    vertical = detect_vertical(text)
                elif vertical_choice == "Todas as lojas":
                    vertical = None
                else:
                    vertical = vertical_choice
                results, errors = search_all(term, excluded=excluded, use_cache=use_cache, hint=hint, vertical=vertical)
                eq = eq or g1_future.result()
                req, specs = finalize_request(req, eq)
            if infer_wanted_category(term):
                budget_max = req.max_budget
                titles = [r.title for r in sorted(results, key=lambda r: r.price)
                          if not (budget_max and r.price > budget_max)]
                classify_titles(titles)
        st.session_state["search"] = {
            "eq": eq,
            "request": req,
            "specs": specs,
            "term": term,
            "results": results,
            "errors": errors,
            "llm_failed": G1_RUN["llm_failed"],
            "vertical": vertical,
        }

    # ---------- Resultados (re-ordenados sem voltar a pesquisar) ----------
    data = st.session_state.get("search")
    if data:
        sort = "cheapest" if sort_label == "Menor custo total" else "best_value"
        eq, term = data["eq"], data["term"]
        req, specs = data["request"], data["specs"]
        ranked, rejected, wanted = run_group3(
            data["results"], wanted_text=term, max_budget=req.max_budget,
            specs=specs, sort=sort, vertical=data.get("vertical"), request=req,
        )

        st.caption(f"Tipo de pesquisa: {data.get('vertical') or 'todas as lojas'}")
        if data.get("llm_failed"):
            st.warning(
                "Ollama indisponível: o pedido foi interpretado só por regras (orçamento, estado, marca e "
                "requisitos numéricos); preferências mais subtis podem ter-se perdido."
            )
        if LAST_RUN.get("skipped_titles"):
            st.warning(
                f"{LAST_RUN['skipped_titles']} títulos ficaram sem classificação por LLM (limite de tempo): "
                "podem aparecer artigos de outra categoria. Volta a pesquisar daqui a 5 minutos para completar."
            )
        if LAST_RUN["failed_titles"]:
            st.warning(
                f"{LAST_RUN['failed_titles']} títulos classificados só pelas regras (Ollama desligado?)."
            )

        ranked = [i for i in ranked if i.product.condition in conditions]

        hidden = 0
        if only_own:
            before = len(ranked)
            ranked = [i for i in ranked
                      if not is_external_seller(i.product.store, i.product.seller_name)]
            hidden = before - len(ranked)

        budget = f"{req.max_budget:.0f} €" if req.max_budget else "sem limite"
        st.caption(f"Interpretação do pedido: {describe(req)}")
        st.caption(f"Pesquisa: **{term}** · orçamento máx.: **{budget}** · categoria: **{wanted or 'qualquer'}**")
        if hidden:
            st.caption(f"{hidden} artigo(s) escondido(s) por terem vendedor externo.")

        if not ranked:
            st.warning("Sem resultados dentro dos teus critérios. Vê os rejeitados abaixo.")
        else:
            rows = [
                {
                    "Score": i.score,
                    "Total (€)": i.total_cost,
                    "Loja": i.product.store,
                    "Vendedor": i.product.seller_name,
                    "Estado": i.product.condition,
                    "Título": i.product.title,
                    "Imagem": i.product.image_url,
                    "Link": i.product.url,
                }
                for i in ranked
            ]
            event = st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="results_table",
                column_config={
                    "Imagem": st.column_config.ImageColumn("Foto"),
                    "Link": st.column_config.LinkColumn("Ver", display_text="Abrir"),
                    "Total (€)": st.column_config.NumberColumn(format="%.2f €"),
                    "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                },
            )

            avisos = sorted({w for i in ranked for w in i.warnings})
            for w in avisos:
                st.caption(f"⚠️ {w}")

            # ---------- Guardar nos favoritos ----------
            selected = event.selection.rows
            if selected and selected[0] < len(ranked):
                chosen = ranked[selected[0]].product
                st.markdown(f"**Selecionado:** {chosen.title}")

                with SessionLocal() as db:
                    folder_names = [f.name for f in list_folders(db)] or ["Geral"]
                c1, c2, c3 = st.columns(3)
                folder = c1.selectbox("Pasta", folder_names, key="fav_folder")
                new_folder = c2.text_input("Ou cria uma pasta nova", key="fav_new_folder")
                target = c3.number_input("Preço-alvo (€, 0 = sem alvo)", min_value=0.0,
                                         value=0.0, step=10.0, key="fav_target")
                note = st.text_input("Nota (opcional)", key="fav_note")

                if st.button("⭐ Guardar nos favoritos"):
                    try:
                        with SessionLocal() as db:
                            add_favorite(
                                db, chosen.store, chosen.external_id,
                                folder_name=new_folder.strip() or folder,
                                note=note.strip() or None,
                                target_price=target or None,
                            )
                        st.success("Guardado nos favoritos.")
                    except FavoriteError as e:
                        st.error(str(e))
            else:
                st.caption("Seleciona uma linha da tabela (caixa à esquerda) para a guardar nos favoritos.")

        for loja, erro in data["errors"].items():
            if erro == NO_RESULTS:
                st.caption(f"Sem resultados em {loja}.")
            else:
                st.error(f"Erro em {loja}: {erro}")

        if len(ranked) < MIN_RESULTS and rejected:
            close = near_misses(rejected, wanted, req.max_budget, min_budget=req.min_budget)
            if close:
                st.info("Poucos resultados. Quase cumprem o pedido (só falham estado, marca ou orçamento mínimo):")
                st.dataframe(
                    pd.DataFrame([
                        {"Preço (€)": r.product.price, "Loja": r.product.store, "Título": r.product.title,
                         "Falha": r.reason, "Link": r.product.url}
                        for r in close
                    ]),
                    hide_index=True,
                    column_config={"Link": st.column_config.LinkColumn("Link", display_text="abrir")},
                )

        if rejected:
            with st.expander(f"Rejeitados ({len(rejected)})"):
                st.dataframe(
                    pd.DataFrame([
                        {"Motivo": r.reason, "Loja": r.product.store, "Preço (€)": r.product.price,
                         "Título": r.product.title}
                        for r in rejected
                    ]),
                    hide_index=True,
                )

# =====================================================================
# Separador: Favoritos (com alertas)
# =====================================================================
with tab_fav:
    with SessionLocal() as db:
        folder_names = [f.name for f in list_folders(db)]
        folder_filter = st.selectbox("Pasta", ["Todas"] + folder_names, key="fav_filter")
        items = list_favorites(db, None if folder_filter == "Todas" else folder_filter)
        alerts = check_alerts(db)            # sobre todos os favoritos, qualquer pasta

    if alerts:
        st.subheader("Alertas")
        for a in alerts:
            line = f"**{a.title[:70].strip()}** ({a.store}): {a.message}"
            if a.kind == "suspicious_promo":
                st.warning("⚠️ " + line)
            elif a.kind == "target_reached":
                st.success("🎯 " + line)
            else:
                st.success("📉 " + line)

    if not items:
        st.info("Ainda não tens favoritos nesta pasta. Faz uma pesquisa, seleciona uma linha e guarda-a.")
    else:
        fav_event = st.dataframe(
            pd.DataFrame([
                {
                    "Pasta": f.folder,
                    "Loja": f.store,
                    "Título": f.title,
                    "Último preço (€)": f.last_price,
                    "Preço-alvo (€)": f.target_price,
                    "No alvo": "✅" if f.below_target else "",
                    "Nota": f.note,
                    "Link": f.url,
                }
                for f in items
            ]),
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="fav_table",
            column_config={
                "Link": st.column_config.LinkColumn("Ver", display_text="Abrir"),
                "Último preço (€)": st.column_config.NumberColumn(format="%.2f €"),
                "Preço-alvo (€)": st.column_config.NumberColumn(format="%.2f €"),
            },
        )
        st.caption("O último preço só se atualiza quando voltas a pesquisar o produto. "
                   "É o preço do artigo, sem portes.")

        sel = fav_event.selection.rows
        if sel and sel[0] < len(items):
            fav = items[sel[0]]
            st.markdown(f"**Selecionado:** {fav.title}")
            a_col, b_col, c_col = st.columns([2, 1, 1])
            new_target = a_col.number_input("Novo preço-alvo (€, 0 = sem alvo)", min_value=0.0,
                                            value=float(fav.target_price or 0.0), step=10.0,
                                            key=f"target_{fav.id}")
            if b_col.button("Atualizar alvo"):
                try:
                    with SessionLocal() as db:
                        set_target_price(db, fav.id, new_target or None)
                    st.rerun()
                except FavoriteError as e:
                    st.error(str(e))
            if c_col.button("🗑️ Remover"):
                with SessionLocal() as db:
                    remove_favorite(db, fav.id)
                st.rerun()

# ---------- Estado das lojas (barra lateral), com o resultado da última pesquisa ----------
_last = st.session_state.get("search") or {}
_counts: dict[str, int] = {}
for _r in _last.get("results", []):
    _counts[_r.store] = _counts.get(_r.store, 0) + 1
with store_box:
    with st.expander(f"Lojas disponíveis ({len(STORES)})"):
        st.dataframe(
            pd.DataFrame(store_overview(STORES, excluded, _counts, _last.get("errors"), NO_RESULTS)),
            hide_index=True,
        )

