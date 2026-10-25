# Ai_universal_shopping — agregador de compras com IA

Agregador de compras **100% local** (Python + Ollama), para uso pessoal, que pesquisa o mesmo artigo em várias lojas online, limpa e valida os resultados, calcula o custo real e ordena por valor. Pensado para poder escalar mais tarde para SaaS ou afiliados.

> **Estado:** projeto pessoal em desenvolvimento, não é um produto acabado. Interface em Streamlit e script de linha de comandos funcionais; a API FastAPI ainda não está implementada.

---

## Índice

1. [O que faz](#1-o-que-faz)
2. [Como funciona (pipeline)](#2-como-funciona-pipeline)
3. [Requisitos](#3-requisitos)
4. [Instalação](#4-instalação)
5. [Configuração (`.env`)](#5-configuração-env)
6. [Utilização](#6-utilização)
7. [Estrutura do projeto](#7-estrutura-do-projeto)
8. [Lojas suportadas](#8-lojas-suportadas)
9. [Adicionar uma loja nova](#9-adicionar-uma-loja-nova)
10. [Os agentes](#10-os-agentes)
11. [Base de dados](#11-base-de-dados)
12. [Testes](#12-testes)
13. [Scripts úteis](#13-scripts-úteis)
14. [Decisões de arquitetura](#14-decisões-de-arquitetura)
15. [Limitações conhecidas](#15-limitações-conhecidas)
16. [Roadmap](#16-roadmap)
17. [Licença](#17-licença)
18. [Aviso legal](#18-aviso-legal)

---

## 1. O que faz

- Recebe um pedido em linguagem natural, por exemplo:
  `"Quero um portátil gaming da Asus ou Lenovo com RTX 4060, 16GB de RAM e SSD 512GB, novo, entre 800 e 1200€, de preferência preto"`.
- Interpreta o pedido **por regras, sem LLM**: termo de pesquisa, marcas, requisitos numéricos (RAM, SSD, ecrã, CPU), estado (novo/recondicionado), orçamento mínimo e máximo e preferências (dão bónus, não eliminam).
- Pesquisa em paralelo em várias lojas (hardware, motos, carros, geral) com Playwright.
- Filtra lixo: acessórios, brinquedos, peças, livros, preços atípicos, anúncios que não são o artigo pedido.
- Classifica a categoria do artigo (regras rápidas, depois LLM local, depois regras antigas).
- Calcula o custo (preço + portes + impostos) e ordena por valor.
- Mostra também o que **quase cumpre** o pedido quando há poucos resultados.
- Guarda histórico de preços, favoritos com preço-alvo e alertas.

**Checkout:** o sistema **não compra automaticamente**. Redireciona para a página do produto (afiliados mais tarde).

### Os 5 pilares

| # | Pilar | Estado |
|---|---|---|
| 1 | Histórico de preços | Feito |
| 2 | Calculadora IVA/IOSS/alfândega | Parcial (PT/EU = 0; extra-UE configurável, não testado com loja real) |
| 3 | Garantias | Por fazer |
| 4 | Filtro de vendedores terceiros | Parcial (só Worten) |
| 5 | Cache local | Feito |

---

## 2. Como funciona (pipeline)

```
Pedido em texto
   │
   ▼
Grupo 1 – Input ........ request_parser (regras) + parser/specs (LLM, complemento)
   │
   ▼
Grupo 2 – Pesquisa ..... lojas em paralelo (Playwright) → lojas "solo" em sequência
   │                      cache 60 min · retries · deteção de bloqueio · relevant()
   ▼
Grupo 3 – Lógica ....... apply_costs → url_safety → split_not_the_item → validate
   │                      → request_filters → dedupe → split_non_vehicles
   │                      → mark_books → split_outliers → rank
   ▼
Resultados + rejeitados + "quase cumprem"  (Streamlit / search_smart)
```

Em paralelo com as lojas corre o Grupo 1 (LLM), para não somar tempos.

---

## 3. Requisitos

- Windows (desenvolvido e testado em Windows + CMD), Python **3.11**
- [Ollama](https://ollama.com) com o modelo `llama3.1:8b` (opcional: sem Ollama o sistema degrada para regras e mostra aviso)
- Chromium do Playwright
- Hardware de referência: Ryzen 5 3600, 16 GB RAM, RTX 3050 8 GB (um lote de 10 títulos no LLM demora cerca de 15 s)

Dependências Python (`requirements.txt`): ollama, playwright, beautifulsoup4, lxml, httpx, fake-useragent, SQLAlchemy>=2.0, fastapi, uvicorn[standard], pydantic, pydantic-settings, python-dotenv, streamlit, pandas, tenacity, loguru, rich, pytest.

---

## 4. Instalação

```cmd
git clone https://github.com/Renny3060/Ai_universal_shopping.git
cd Ai_universal_shopping
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
python -m backend.db.init_db
```

Ollama (noutro CMD, deixar a correr):

```cmd
ollama pull llama3.1:8b
ollama serve
```

Verificar que o LLM responde:

```cmd
python -c "from backend.agents.llm import ping; print(ping())"
```
Deve imprimir `OK`.

> Ativar **sempre** o venv (`(venv)` no prompt) e usar `python -m ...` e `python -m pytest`.

---

## 5. Configuração (`.env`)

| Variável | Valor típico | Descrição |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endereço do Ollama |
| `OLLAMA_MODEL` | `llama3.1:8b` | Modelo local |
| `DEFAULT_COUNTRY` | `PT` | País por defeito |
| `DEFAULT_CURRENCY` | `EUR` | Moeda por defeito |
| `CACHE_TTL_MINUTES` | `60` | Validade da cache de pesquisa |
| `MAX_PAGES` | `2` | Páginas por loja (só em lojas com `page_url`) |
| `LLM_MAX_TITLES` | `60` | (opcional) Máx. de títulos enviados ao LLM por pesquisa |
| `CATEGORY_COMPACT` | `0` | (opcional) Desliga o formato compacto das categorias |

O `.env` nunca vai para o Git (há um `.env.example` como modelo). O `.gitignore` exclui `venv/`, `.env`, a base de dados e tudo o que é gerado em `data/`; só o registo de lojas automáticas (`data/stores_auto.json`) faz parte do repositório.

---

## 6. Utilização

### Interface (Streamlit)

```cmd
streamlit run frontend\app.py
```

- Separadores **Pesquisa** e **Favoritos**
- Barra lateral: lojas a excluir, ordenação, estado, "só vendidos pela própria loja", cache, **Tipo de pesquisa** (Automático, Todas, tech, general, cars, moto) e painel **Lojas disponíveis** (tipo, origem, estado e resultado da última pesquisa)
- Tabela de resultados com avisos, expander de rejeitados com motivo e lista **"Quase cumprem o pedido"** quando há menos de 3 resultados
- Favoritos com pastas, nota, preço-alvo e alertas (preço-alvo, descida, promoção falsa)
- Avisos amarelos quando o Ollama está em baixo

### Linha de comandos

```cmd
python -m scripts.search_smart "RTX 5060 até 650€"
python -m scripts.search_smart "RTX 5060 até 650€" --barato
python -m scripts.search_smart "golf gti até 12000€"
python -m scripts.search_smart "lego ninjago até 30€" --vertical general
python -m scripts.search_smart "audi tt até 15000€" --min-preco 1500
```

Opções: `--barato` (ordena só por custo total), `--vertical tech|general|cars|moto|todas`, `--min-preco N`. Sem `--vertical`, a vertical é detetada automaticamente por palavras (sem LLM). O script mostra a linha "Interpretação:", os 15 melhores, rejeitados por motivo, avisos e tempos por fase.

---

## 7. Estrutura do projeto

```
universal_ai_shopping/
├── .env.example, .gitignore, requirements.txt, LICENSE, README.md, conftest.py
├── data/                         stores_auto.json (versionado); o resto é gerado em runtime
├── backend/
│   ├── config.py, main.py        (main.py ainda vazio)
│   ├── api/                      favorites.py, profile.py, search.py  (vazios, FastAPI por fazer)
│   ├── db/                       database.py, models.py, init_db.py
│   ├── schemas/                  search.py, product.py, ranking.py
│   ├── services/                 cache, price_tracker, tax_calculator, url_safety, favorites, alerts,
│   │                             store_health, store_overview  (vendor_filter, warranty: vazios)
│   ├── utils/                    parsing, query_cleaning, text_normalize, brands
│   └── agents/
│       ├── llm.py, crew.py       (crew.py vazio, reservado; CrewAI não é usado)
│       ├── group1_input/         parser_agent, specs_agent, compatibility_agent, profile_agent,
│       │                         request_parser, pipeline
│       ├── group2_search/        anti_block, browser, base_scraper, configurable_scraper, stores,
│       │                         aggregator, block_detector, jsonld, discovery, batch_discovery,
│       │                         auto_selectors, plausibility
│       ├── group3_logic/         categories, category_llm, fast_category, financial_agent,
│       │                         validator_agent, scoring_agent, spec_check, dedupe, sellers,
│       │                         outliers, vertical_rules, book_rules, relevance_rules,
│       │                         request_filters, near_misses, pipeline
│       └── group4_output/        (vazio)
├── frontend/app.py               Interface Streamlit
├── scripts/                      Pesquisa, diagnóstico e descoberta de lojas (secção 13)
└── tests/                        Suite pytest
```

---

## 8. Lojas suportadas

18 lojas em `STORES` (12 configuradas à mão e 6 de deteção automática), repartidas por verticais (`tech`, `general`, `cars`, `moto`):

| Loja | Leitura | Verticais | Notas |
|---|---|---|---|
| pcdiga | CSS | tech | |
| worten | CSS | tech | Vendedor por "Vendido por"; intermitente |
| olx | CSS | tech, general, cars, moto | Anúncios de particulares (aviso); inclui Standvirtual |
| aliexpress | CSS | tech, general | `rank_penalty=25`; impostos ainda a 0 |
| amazon_es | CSS | tech, general | Loja **solo** (corre sozinha, no fim) |
| motocard | JSON-LD | moto | `/pt/search`, `trust_search` |
| standvirtual | CSS | cars | |
| mediamarkt | JSON-LD | tech | Loja espanhola |
| globaldata | CSS | tech | |
| assismatica | CSS | tech | "Tempo esgotado" em pesquisas longas |
| mhr | CSS | tech | Só 1 página |
| imperiomultimedia | CSS | tech | Só 1 página; "sem produtos" intermitente |
| motoscoot, custojusto, prof, vertbaudet | Automática | vários | Geradas por `auto_selectors` (`data/stores_auto.json`) |
| bertrand, almedina | Automática | general | `kind="books"`: livros ficam no fim |

Lojas automáticas são desativadas após 5 falhas seguidas (`store_health`).

---

## 9. Adicionar uma loja nova

Regra de ouro: **nunca inventar seletores nem URLs**; tirá-los sempre de HTML real.

1. **Descobrir o URL de pesquisa** (abre a loja, escreve o termo na caixa e lê o URL):
   ```cmd
   python -m scripts.discover_store "https://www.loja.pt/" "termo" [--visible]
   ```
   Em lote: `python -m scripts.discover_batch [--limit N] [--resume] [--only nome] [--visible]` (lê `data/lojas_candidatas.csv`, uma lista de lojas candidatas que tens de fornecer; não vem no repositório).
2. **Testar JSON-LD:**
   ```cmd
   python -m scripts.probe_store "URL_DE_PESQUISA"
   ```
   Se servir, a entrada só precisa de `search_url` e `base_url` (sem `card`).
3. **Se não servir**, gerar ou escrever seletores CSS a partir do HTML guardado em `data\debug\`:
   ```cmd
   python -m scripts.inspect_store "URL_DA_LISTA"
   python -m scripts.auto_selectors
   python -m scripts.test_generated
   python -m scripts.promote_generated
   ```
4. **Validar:** `python -m scripts.diag_scraper nome_da_loja "termo"` e `python -m scripts.integration_stores`.

### Chaves de configuração por loja (`ConfigurableScraper`)

`search_url`, `base_url`, `page_url`, `card`, `title`, `price`, `link`, `image`, `title_attr`, `price_attr`, `id_attr`, `wait`, `q_sep`, `default_condition`, `id_regex`, `url_strip_query`, `url_template`, `seller_label`, `own_seller_names`, `use_hint`, `country`, `currency`, `verticals`, `extra_domains`, `private_listings`, `trust_search`, `kind`, `rank_penalty` e a marca de loja "solo".

- Sem `card` → leitura por JSON-LD (schema.org).
- `{q}` = termo (com `q_sep` se definido, senão `quote_plus`); `{qp}` = `quote_plus`; `{page}` = página.
- Lojas de livros novas têm de ser acrescentadas a `_STORE_KINDS` em `stores.py`.

---

## 10. Os agentes

Equipa planeada de 20 agentes em 4 grupos. Só alguns usam LLM; os restantes são Python determinístico.

| Grupo | Agentes | Estado |
|---|---|---|
| **1 – Input** | 1 Parser, 2 Especificações, 3 Compatibilidade, 4 Perfil | Feitos (+ `request_parser` por regras) |
| **2 – Pesquisa** | 5 Amazon EU, 6 AliExpress, 7 eBay, 8 Lojas Locais, 9 Agregadores, 10 Envio, 11 Anti-Bloqueio, 12 Verificador de Stock | Amazon.es, AliExpress, lojas locais e anti-bloqueio feitos; eBay, envio e stock por fazer |
| **3 – Lógica** | 13 Financeiro, 14 Segurança de URL, 15 Custo-Benefício, 16 Validador de Requisitos, 17 Alertas | 13 a 16 feitos; 17 só parcial (serviço de alertas, falta agendador) |
| **4 – Output** | 18 Formatador de UI, 19 Filtros Dinâmicos, 20 Gestor de Favoritos | Favoritos feito na interface; 18 e 19 por fazer |

Usam LLM: Parser (1), Especificações (2) e classificação de categoria (só como fallback depois das regras rápidas).

### Regras e filtros do Grupo 3 (resumo)

- **`relevant()`**: números de modelo têm de estar no título; sufixos Ti/Super/XT/XTX têm de coincidir; capacidades ignoradas; palavras curtas ("tt", "x5") contam como palavra inteira.
- **`relevance_rules`**: regra do "para / compatível com" (acessórios) e léxico de brinquedos/merchandising (não aplicado em `general`).
- **`fast_category`**: classifica sem LLM quando o título começa por palavra inequívoca; SSD só é categoria quando não há sinais de computador completo.
- **`validator_agent`**: rejeita por categoria errada, acima do orçamento e requisitos numéricos (RAM, SSD, VRAM, ecrã).
- **`request_filters`**: marca, estado, orçamento mínimo, família de CPU; preferências dão bónus.
- **`vertical_rules`**: padrões de peças para carros/motos e preço mínimo (`cars` 1000 €, `moto` 20 €, `general` 2 €), só em lojas mistas.
- **`book_rules`**: livros vão para o fim quando o pedido não fala de livros.
- **`outliers`**: rejeita preços abaixo de 35% da mediana (mín. 8 itens, só com categoria pedida).
- **`near_misses`**: lista o que falha só por critérios moles (estado, marca, mínimo), ordenado pela distância ao pedido.
- **`scoring_agent`**: 80% preço + 20% estado (novo 1.0, recondicionado 0.75, usado 0.3); penalização por loja; avisos passam para o fim.
- Outlet, caixa aberta, open box e "grade A/B/C" contam como **recondicionado**.

---

## 11. Base de dados

SQLite + SQLAlchemy 2.0 (`data/shopping.db`).

| Tabela | Conteúdo |
|---|---|
| `user_profile` | Perfil do utilizador |
| `products` | Única por `store` + `external_id` |
| `price_history` | Histórico de preços; `shipping_known` (`NULL` antigo, `False` desconhecidos, `True` conhecidos) |
| `favorite_folders`, `favorites` | Pastas, nota, preço-alvo |
| `search_cache` | Cache de pesquisa por hash `loja\|termo` (TTL 60 min) e categorias do LLM |

Inicializar: `python -m backend.db.init_db`. Migração do campo de portes: `python -m scripts.migrate_shipping_known` (idempotente).

---

## 12. Testes

```cmd
python -m pytest tests -q
```

A suite tem **314 testes em 59 ficheiros** (`tests/test_*.py`). Não precisam de Ollama, de browser nem de rede. O `conftest.py` desliga o LLM nas categorias para os testes serem determinísticos.

Estado geral do ambiente: `python -m scripts.diagnostico`.

---

## 13. Scripts úteis

| Script | Função |
|---|---|
| `search_smart` | Pesquisa completa (pipeline inteiro) em linha de comandos |
| `search_all` | Só pesquisa nas lojas |
| `integration_stores` | Fase A (cada loja sozinha) e Fase B (todas juntas); `--so-juntas`, `--so-individual`, `--vertical` |
| `store_status` | Saúde das lojas |
| `diag_scraper` | Scraper de uma loja, sem cache, mostra exceções |
| `diag_live`, `diag_parse` | Fetch + parse ao vivo / sobre HTML guardado |
| `probe_store` | Testa se uma loja serve JSON-LD |
| `inspect_store`, `show_card`, `analyze_html` | Ajudas para tirar seletores |
| `discover_store`, `discover_batch` | Descoberta do URL de pesquisa |
| `auto_selectors`, `test_generated`, `promote_generated` | Geração e promoção de lojas automáticas |
| `compare_categories`, `test_category_llm`, `bench_fast_category`, `bench_compact` | Medição de categorias |
| `diagnostico` | Estado geral (venv, init, Ollama, git, testes) |
| `migrate_shipping_known`, `aplicar_correcoes` | Migrações/correções pontuais |

Para medir tempos reais, usar sempre termos novos (a cache de categorias esconde o tempo do LLM).

---

## 14. Decisões de arquitetura

1. **Ollama direto com saída estruturada** (`format=schema` + validação Pydantic + 3 tentativas com `tenacity`); timeout 120 s; `keep_alive="30m"`. CrewAI **não é usado**.
2. **Abordagem híbrida:** scraping para preços e stock; categoria por regras rápidas → LLM → regras antigas.
3. **Playwright apenas** para scraping, com user-agent aleatório e locale `pt-PT`.
4. **Scraper configurável por loja:** loja nova = uma entrada em `stores.py`.
5. **Sem Ollama o sistema degrada, não pára.**
6. **Interpretador de pedidos determinístico**, instantâneo e sem LLM.
7. **Lojas "solo":** as lojas normais correm em paralelo; as "solo" (hoje `amazon_es`) depois, em sequência, porque em paralelo eram bloqueadas.
8. **Verticais por loja** e deteção automática da vertical por palavras.
9. **Regras de veículos e preço mínimo só em lojas mistas** (OLX, CustoJusto).
10. **Portes a 0 por agora, sem valores fixos por loja:** o total não inclui portes e mostra o aviso "Portes desconhecidos". Decisão final no fim do projeto.
11. **Tempos controlados:** orçamento de scraping, timeout por pedido ao LLM, lotes de 10 títulos, no máximo 60 títulos por pesquisa no LLM, e após um timeout os lotes seguintes não são tentados. Pesquisa com teto de 10 minutos.
12. **Lojas automáticas** em `data/stores_auto.json`, sem substituir lojas escritas à mão.
13. **Lojas sem produtos não são erro** (cinzento), exceto resposta vazia suspeita de bloqueio (vermelho).

---

## 15. Limitações conhecidas

- 2 páginas por loja, só nas lojas com `page_url` (MHR e Império Multimédia só 1).
- **Portes a 0 no total**; impostos a 0 em todas as lojas (incluindo AliExpress e Amazon.es).
- A pontuação só usa preço, estado, penalização por loja e bónus de preferências; faltam reputação do vendedor, garantia e prazo de entrega.
- Carros e motos: sem categoria nem LLM, só regex de peças e preço mínimo.
- Vendedor só identificado na Worten.
- Só existem as verticais `tech`, `general`, `cars`, `moto`.
- Títulos fora dos 60 mais baratos usam as regras antigas de categoria.
- O LLM de 8B erra em casos ambíguos e é enganado por alguns títulos.
- Pedidos muito específicos podem dar 0 resultados (a lista "quase cumprem" ajuda).
- **Problema aberto:** artigos de substituição baratos da AliExpress (ex.: ventoinha "rtx4070" a 12,65 €) podem chegar ao topo quando há poucos resultados.
- **Worten:** pode devolver artigos "indisponíveis online" e preços com cupão, repetidos por vendedor.
- Lojas intermitentes: Worten, Império Multimédia, Assismática (tempo esgotado).
- JSON-LD não é universal; Cloudflare/DataDome/CAPTCHA bloqueiam cerca de 18% das lojas candidatas.
- Tempo típico de uma pesquisa com termo novo: cerca de 2 a 3,5 minutos (Grupo 1 + lojas ~110 s).

---

## 16. Roadmap

**Curto prazo**
1. Corrigir peças de substituição a ganhar o ranking (léxico de peças e/ou preço atípico com menos itens).
2. Correr a suite completa depois da atualização 28 e confirmar commits.
3. Worten: tratar artigos indisponíveis, cupão e duplicados por vendedor.
4. Reduzir o tempo do Grupo 1 + lojas (esperas, retries, lojas lentas).
5. Loja Clickfiel (precisa do HTML real da página de resultados).

**Médio prazo**
- Streaming de resultados para a interface (mostrar já e refinar depois) ou modelo mais pequeno só para categorias.
- Lojas `precisa_css` por prioridade: motos (Caparica Peles, Motoponto, Motoblouz), hardware (Life Informatica, Ibertronica), depois outras categorias.
- Pilares 3 e 4: reputação do vendedor e garantia (`warranty.py`, `vendor_filter.py`).
- Grupo 4: Filtros Dinâmicos (19), Formatador de UI (18), polir Favoritos (20).

**Longo prazo**
- Agente de Alertas (17) com agendador e dados reais ao longo do tempo.
- Portes e IVA reais (incluindo `region` da AliExpress).
- Verificador de stock, API FastAPI (`main.py`, `api/*`), eBay, categorias novas (moda, casa, desporto), compatibilidade para builds de PC completas, CrewAI se fizer falta.
- Modelo comercial (SaaS ou afiliados) só depois de o MVP pessoal estar estável.

**Decisões que ficam para o fim:** anti-bot (proxies, mais pausas ou ignorar lojas que bloqueiam), limpeza periódica da cache, qualidade vs velocidade.

---

## 17. Licença

**Todos os direitos reservados.** O código está público apenas para consulta e avaliação (portfólio). Não é permitido copiar, modificar, redistribuir nem reutilizar sem autorização prévia por escrito. Ver [LICENSE](LICENSE).

---

## 18. Aviso legal

Uso pessoal. O scraping pode violar os termos de utilização de algumas lojas: o projeto usa pausas, retries moderados e cache para reduzir carga, e não contorna CAPTCHAs. Os preços e a disponibilidade mostrados podem estar desatualizados ou incorretos; confirmar sempre na página da loja antes de comprar.
