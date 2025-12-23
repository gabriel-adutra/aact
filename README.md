# ClinicalTrials.gov → Neo4j (AACT ETL)

## Sobre o Projeto
Este serviço Python assíncrono (contenizado) realiza um ETL completo a partir do AACT (PostgreSQL público do ClinicalTrials.gov) para Neo4j, consolidando estudos clínicos, drogas, condições e patrocinadores. O fluxo contempla:
- Ingestão relacional (AACT) com query parametrizada e agregação (`json_agg`) para evitar “explosão de joins”.
- Transformação e normalização (limpeza de texto + inferência leve de rota/dosagem via regras).
- Carga em lote no Neo4j, com constraints/indexes para garantir idempotência e performance.
- Consultas Cypher de demonstração para validar o grafo.

## Arquitetura (Separação de Responsabilidades)

### Módulos principais
- `config/extract_trials.sql` — Query única e declarativa de extração (AACT → JSON agregado por estudo).
- `config/text_rules.yaml` — Regras declarativas de inferência (rota/dosagem) baseadas em palavras‑chave.
- `src/db/aact_client.py` — Adapter de leitura AACT (PostgreSQL), streaming em batches.
- `src/processing/data_cleaner.py` — Normalização de campos e chamada do parser de texto.
- `src/processing/text_parser.py` — Inferência rule‑based de rota/dosagem a partir de texto livre.
- `src/db/neo4j_client.py` — Adapter de escrita Neo4j (constraints, índices, carga em lote via UNWIND).
- `src/main.py` — Orquestrador do pipeline (Extract → Transform → Load) com batch e limite configuráveis.
- `queries.cypher` — Consultas de demonstração para validação rápida no Neo4j.

### Características do Sistema
- **Batch & Idempotente:** MERGE em todas as entidades; repetir o ETL não duplica dados.
- **Config‑driven:** SQL, regras de texto e variáveis sensíveis em arquivos dedicados (`.env`).
- **Leve & Reprodutível:** Rule‑based NLP em vez de LLM/NER pesado; imagem Docker enxuta.
- **Resiliente:** Constraints e índices aplicados automaticamente; logs claros de progresso.

## Decisões e Racional

1) **Fonte AACT direta (Postgres público) vs. dump de 2GB**
   - Evita versionar/baixar binários enormes; experiência “clone & run”.

2) **Query relacional → JSON agregado**
   - `json_agg` no Postgres entrega 1 estudo com listas de drogas/condições/patrocinadores, evitando reagrupamento manual no Python.

3) **Inferência de rota/dosagem via regras simples**
   - Vantagens: leve, offline, explicável.  
   - Limitação: cobertura baixa quando não há texto rico; muitos `Unknown`.  
   - Futuro: NER/LLM (BioBERT/SciSpacy) ou analisar também o nome da droga para hints de forma/rota.

4) **Incluir DRUG e BIOLOGICAL**
   - Abrange small molecules e biológicos; evita perder ensaios de vacinas/anticorpos.  
   - Documentado no README para justificar a definição de “Clinical‑stage drugs”.

5) **Placebo mantido**
   - Fidelidade à fonte. Poderia filtrar, mas manter facilita auditoria e evita decisões de negócio implícitas.

6) **Normalização de nomes com `.title()`**
   - Simples e suficiente para o escopo; pode “simplificar” acrônimos (dnaJ → Dnaj). Limitação registrada.

## Como o Sistema Funciona

1) **Ingestão (AACT → Python)**  
   - `config/extract_trials.sql` filtra estudos intervencionais em fases PHASE1/2/3/4 (inclui PHASE1/PHASE2, PHASE2/PHASE3) e `intervention_type IN ('DRUG','BIOLOGICAL')`.  
   - Agrega drogas, condições e patrocinadores por estudo (`json_agg`).

2) **Transformação (Python)**  
   - `DataCleaner` normaliza textos (trim, Title Case básico) e deduplica condições.  
   - `TextParser` aplica regras de rota/dosagem sobre a descrição da intervenção; se vazio, retorna `Unknown`.

3) **Carga (Neo4j)**  
   - Constraints/Índices criados automaticamente (nct_id, nome de Drug/Condition/Organization).  
   - Carga em lote com `UNWIND $batch` e propriedades de rota/dosagem na relação `STUDIED_IN`.

4) **Validação (Queries)**  
   - `queries.cypher` contém consultas para top drugs, visão por empresa, visão por condição e cobertura de rota/dosagem.

## Modelagem de Dados (Grafo)
- Nós: `(:Trial {nct_id, title, phase, status})`, `(:Drug {name})`, `(:Condition {name})`, `(:Organization {name})`
- Relações:
  - `(:Drug)-[:STUDIED_IN {route?, dosage_form?}]->(:Trial)`
  - `(:Trial)-[:STUDIES_CONDITION]->(:Condition)`
  - `(:Trial)-[:SPONSORED_BY {class?}]->(:Organization)`
- Constraints/Índices: unicidade em nct_id e nomes; índices em phase/status.

## Pré-requisitos
- Docker + Docker Compose.
- Conta AACT para credenciais Postgres (criar em https://aact.ctti-clinicaltrials.org/).

Exemplo de `.env` (não versionar):
```
AACT_HOST=aact-db.ctti-clinicaltrials.org
AACT_PORT=5432
AACT_DB=aact
AACT_USER=SEU_USUARIO
AACT_PASSWORD=SUASENHA

NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## Como Rodar (End-to-End)
1) Build:
```
docker compose build etl
```
2) Executar ETL (default: 1000 estudos, batch=500):
```
docker compose run --rm etl python src/main.py
```
3) Acessar Neo4j Browser:
- URL: http://localhost:7474  
- User: `neo4j`  
- Pass: `password` (ajuste no `.env` se quiser)

4) Consultas de Demonstração (também em `queries.cypher`):
- Top drugs:
```
MATCH (d:Drug)<-[:STUDIED_IN]-(t:Trial)
RETURN d.name AS drug, count(t) AS trials
ORDER BY trials DESC
LIMIT 10;
```
- Por empresa (ex.: Novartis):
```
MATCH (o:Organization {name: "Novartis"})<-[:SPONSORED_BY]-(t:Trial)
OPTIONAL MATCH (t)-[:STUDIED_IN]->(d:Drug)
OPTIONAL MATCH (t)-[:STUDIES_CONDITION]->(c:Condition)
RETURN o.name, collect(DISTINCT d.name) AS drugs, collect(DISTINCT c.name) AS conditions;
```
- Por condição (ex.: Alzheimer Disease):
```
MATCH (c:Condition {name: "Alzheimer Disease"})<-[:STUDIES_CONDITION]-(t:Trial)-[:STUDIED_IN]->(d:Drug)
RETURN d.name AS drug, collect(DISTINCT t.phase) AS phases, count(DISTINCT t) AS trial_count
ORDER BY trial_count DESC;
```
- Cobertura rota/dosagem:
```
MATCH ()-[r:STUDIED_IN]->()
RETURN
  count(r) AS total_relationships,
  SUM(CASE WHEN r.route IS NOT NULL AND r.route <> "Unknown" THEN 1 ELSE 0 END) AS with_route,
  SUM(CASE WHEN r.dosage_form IS NOT NULL AND r.dosage_form <> "Unknown" THEN 1 ELSE 0 END) AS with_dosage_form;
```

## Ajustes de Volume
- Editar `run_pipeline(limit=..., batch_size=...)` em `src/main.py` e rodar novamente:
```
docker compose run --rm etl python src/main.py
```
- Carga é idempotente (MERGE evita duplicatas).

## Limitações Conhecidas
- Baixa cobertura de rota/dosagem por falta de texto rico nas descrições de intervenção; muitos `Unknown`.
- `.title()` pode simplificar acrônimos (ex.: dnaJ → Dnaj).
- Placebo permanece como Drug (fidelidade à fonte); pode ser filtrado se desejado.
- Não usamos LLM/NER pesado para manter imagem leve e execução offline; limitação documentada.

## Próximos Passos (se houvesse mais tempo)
- NER/LLM (BioBERT/SciSpacy) para melhorar rota/dosagem.
- Heurística no nome da droga para extrair forma/rota sem alterar o identificador.
- Métricas automáticas (nós/arestas criados, coverage de campos).
- Ingestão incremental e orquestração (Airflow/Prefect).
# ClinicalTrials.gov → Neo4j (AACT ETL)

## Visão Geral
Pipeline em Python que:
1. Extrai estudos clínicos do AACT (Postgres público do ClinicalTrials.gov).
2. Transforma e enriquece (limpeza + inferência de rota/dosagem a partir de texto).
3. Carrega em lote no Neo4j, com constraints/indexes para idempotência e performance.
4. Inclui queries Cypher de demonstração.

## Arquitetura
- **Fonte:** AACT (PostgreSQL público). Consulta parametrizada em `config/extract_trials.sql`.
- **Processamento:** Python (rule-based NLP leve), arquivos de regras em `config/text_rules.yaml`.
- **Alvo:** Neo4j (grafo), carga em lote via `UNWIND`.
- **Conteinerização:** `docker-compose` com serviços `neo4j` e `etl`.

## Decisões e Trade-offs
- **AACT direto (Postgres público)** em vez de dump local de 2GB: zero dependência de arquivo gigante e experiência “clone & run”.
- **Query relacional → JSON aninhado (json_agg)**: o Postgres já agrupa drogas/condições/patrocinadores por estudo, evitando lógica de reagrupamento no Python.
- **Inferência de rota/dosagem via regras (regex/keyword)**:
  - Vantagem: leve, reprodutível offline, explica cada decisão.
  - Limitação: cobertura limitada quando não há texto rico; não é um NER/LLM.
- **Por que não Databricks/LLM/Spacy pesado?**
  - Overkill para o escopo; aumenta dependência externa, custo e latência.
  - Repositório e imagem Docker mais enxutos; foco em clareza e reprodutibilidade.
  - Documentamos a limitação e o caminho de melhoria (usar NER/LLM no futuro).
- **Placebo como droga:** Mantido conforme fonte; decisão de negócio poderia filtrar, mas preservamos fidelidade aos dados.
- **Normalização de nomes:** `.title()` pode simplificar acrônimos (ex: dnaJ → Dnaj). Documentado como limitação aceitável.

## Consulta de Extração (AACT)
Arquivo: `config/extract_trials.sql`
- Filtra **intervention_type IN ('DRUG', 'BIOLOGICAL')** (para cobrir small molecules e biológicos).
- Fases clínicas: `PHASE1`, `PHASE2`, `PHASE3`, `PHASE4`, `PHASE1/PHASE2`, `PHASE2/PHASE3`.
- Estudo intervencional: `study_type = 'INTERVENTIONAL'`.
- Agrupa:
  - `drugs`: lista de `{name, description}`
  - `conditions`: lista de nomes
  - `sponsors`: lista de `{name, class}`

## Inferência de Rota/Dosagem
Arquivo: `config/text_rules.yaml`
- Regras de keywords para `routes` (Oral, Intravenous, Subcutaneous, etc.) e `dosage_forms` (Tablet, Injection, Cream, etc.).
- Aplicado à **description** da intervenção. Se não houver texto, retorna `Unknown`.
- Cobertura observada em 1000 trials: 1.645 relações Trial–Drug, 79 com rota (≈4,8%), 21 com forma (≈1,3%). Limitação documentada: falta de texto rico na fonte.

## Modelo de Grafo (Neo4j)
- Nós: `(:Trial {nct_id})`, `(:Drug {name})`, `(:Condition {name})`, `(:Organization {name})`
- Relações:
  - `(:Drug)-[:STUDIED_IN {route?, dosage_form?}]->(:Trial)`
  - `(:Trial)-[:STUDIES_CONDITION]->(:Condition)`
  - `(:Trial)-[:SPONSORED_BY {class?}]->(:Organization)`
- Constraints/Índices:
  - `Trial.nct_id` UNIQUE
  - `Drug.name` UNIQUE
  - `Condition.name` UNIQUE
  - `Organization.name` UNIQUE
  - Indexes em `Trial.phase`, `Trial.status`

## Pré-requisitos
- Docker + Docker Compose.
- Conta no AACT para obter usuário/senha do Postgres (https://aact.ctti-clinicaltrials.org/). Exemplo de `.env`:
  ```
  AACT_HOST=aact-db.ctti-clinicaltrials.org
  AACT_PORT=5432
  AACT_DB=aact
  AACT_USER=SEU_USUARIO
  AACT_PASSWORD=SUASENHA

  NEO4J_URI=bolt://neo4j:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=password
  ```

## Como Rodar
1) Build:
```
docker compose build etl
```
2) Executar ETL (default 1000 estudos em lotes de 500):
```
docker compose run --rm etl python src/main.py
```
3) Acessar Neo4j Browser:
- URL: http://localhost:7474
- Usuário: `neo4j`
- Senha: `password` (ou altere no `.env` / docker-compose).
4) Rodar queries de exemplo (também em `queries.cypher`):
- Top drugs:
```
MATCH (d:Drug)<-[:STUDIED_IN]-(t:Trial)
RETURN d.name AS drug, count(t) AS trials
ORDER BY trials DESC
LIMIT 10;
```
- Por empresa (ex: Novartis):
```
MATCH (o:Organization {name: "Novartis"})<-[:SPONSORED_BY]-(t:Trial)
OPTIONAL MATCH (t)-[:STUDIED_IN]->(d:Drug)
OPTIONAL MATCH (t)-[:STUDIES_CONDITION]->(c:Condition)
RETURN o.name, collect(DISTINCT d.name) AS drugs, collect(DISTINCT c.name) AS conditions;
```
- Por condição (ex: Alzheimer Disease):
```
MATCH (c:Condition {name: "Alzheimer Disease"})<-[:STUDIES_CONDITION]-(t:Trial)-[:STUDIED_IN]->(d:Drug)
RETURN d.name AS drug, collect(DISTINCT t.phase) AS phases, count(DISTINCT t) AS trial_count
ORDER BY trial_count DESC;
```
- Cobertura de rota/dosagem:
```
MATCH ()-[r:STUDIED_IN]->()
RETURN
  count(r) AS total_relationships,
  SUM(CASE WHEN r.route IS NOT NULL AND r.route <> "Unknown" THEN 1 ELSE 0 END) AS with_route,
  SUM(CASE WHEN r.dosage_form IS NOT NULL AND r.dosage_form <> "Unknown" THEN 1 ELSE 0 END) AS with_dosage_form;
```

## Ajustes de Volume
- Para carregar mais de 1000 estudos, edite `run_pipeline(limit=..., batch_size=...)` em `src/main.py` e rode novamente:
```
docker compose run --rm etl python src/main.py
```
- Carga é idempotente (MERGE evita duplicatas).

## Limitações Conhecidas
- Inferência limitada por falta de texto rico: muitos `Unknown` para rota/dosagem.
- Normalização de nomes via `.title()` pode simplificar acrônimos (ex: dnaJ → Dnaj).
- Placebo permanece como droga (fidelidade à fonte). Opcional filtrar se necessário.
- Não usamos LLM/NER pesado por foco em leveza e reprodutibilidade; documentamos a limitação.

## Decisões e Riscos sobre Rota/Dosagem e Normalização
- Cobertura de rota/dosagem tende a ser baixa porque as descrições de intervenção raramente trazem texto rico. Optamos por regras simples e declarativas (text_rules.yaml) e preferimos `Unknown` a falsos positivos.
- Não usamos LLM/NER pesado: o desafio pede abordagem “razoável” e documentada; priorizamos imagem leve, execução offline e transparência. Futuro: NER/LLM (BioBERT/SciSpacy) ou heurística secundária no nome da droga para hints de forma/rota.
- `.title()` simplifica acrônimos (dnaJ → Dnaj); aceitamos essa limitação para reduzir variações triviais. Futuro: lista de exceções/sinônimos para acrônimos conhecidos.
- Ao iniciar, o Neo4j pode avisar que constraints/índices já existem; é esperado e demonstra a idempotência da criação de schema (`IF NOT EXISTS`).

### Trade-offs de Inferência (rota/forma)
- AI Query / Databricks end-to-end: maior cobertura potencial e facilidades gerenciadas; porém depende de cloud, tem custo/latência e foge da leveza/reprodutibilidade local.
- Modelos locais (BioBERT/SciSpacy): melhor recall que regras; mas aumentam a imagem (GB), o tempo de build e a complexidade operacional.
- Abordagem atual (rule-based): leve, offline, transparente e fácil de auditar; menor recall, mas alinhada ao “reasonable approach” do desafio e mantendo a imagem enxuta.

## Próximos Passos (se houvesse mais tempo)
- Usar NER/LLM (ex.: BioBERT/SciSpacy) para melhorar inferência de rota/dosagem.
- Enriquecer normalização de nomes (tabelas de sinônimos, remoção de sufixos “Tablet”, “Injection” do nome sem afetar identidade).
- Métricas automáticas (quantos nós/arestas criados, coverage de campos).
- Incremental ingestion (delta) e workflow (Airflow/Prefect).

