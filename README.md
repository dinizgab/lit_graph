# LitGraph

## Sobre o app
O sistema tem como objetivo democratizar o acesso a obras literárias clássicas do domínio público, gerando guias de estudo personalizados de acordo com o nível do aluno ou responder perguntas avulsas com base nas obras. A ideia central é que um estudante do ensino médio, um professor preparando uma aula ou um leitor curioso possa obter, em segundos, um material estruturado sobre qualquer obra disponível no Project Gutenberg com resumo, personagens, temas, trechos-chave e perguntas de revisão, tudo embasado em evidências reais do texto original, sem alucinações.

## Usecases principais
### UC-01 — Gerar guia de estudo completo
O caso de uso principal da aplicação. O usuário informa o título da obra, o nível do aluno e o tipo de saída desejada. O sistema executa o workflow completo — recuperando trechos sobre enredo, personagens, temas e passagens-chave — e entrega um documento estruturado com citações do texto original. Exemplo: um professor do ensino médio pedindo um guia completo de Dom Casmurro para usar em sala de aula.

### UC-02 — Responder perguntas avulsas sobre uma obra
O usuário faz uma pergunta direta sobre um livro, sem precisar de um guia completo. O sistema recupera os trechos mais relevantes e responde com citações, funcionando como um assistente de leitura. Exemplo: "Quais são as principais teorias sobre a culpa de Capitu?"

## Diagrama de fluxo do app
![Diagrama de fluxo do app](static/imgs/llm_agents_diagram.png)

---

## MCP — Servidor próprio (`src/mcp/server.py`)

O LitGraph utiliza um servidor MCP próprio implementado com [FastMCP](https://github.com/jlowin/fastmcp), exposto via HTTP em `http://localhost:8000`. O nó `retriever` do grafo LangGraph conecta-se a ele via `langchain-mcp-adapters` com transporte `streamable_http`.

### Ferramentas expostas

| Tool | Entrada | Saída | Descrição |
|------|---------|-------|-----------|
| `get_book_info` | `query: str` | `BookBibliographicContext` | Busca metadados bibliográficos via Gutendex API (título, autores, resumos, assuntos, idiomas) |
| `get_book_historical_context` | `query: str` | `BookHistoricalContext` | Busca contexto histórico via Wikipedia (período, ambiente cultural) |
| `get_book_philosophical_context` | `title, summaries, subjects` | `BookPhilosophicalContext` | Gera temas filosóficos plausíveis associados à obra via LLM |
| `search_book_content` | `query: str, gutenberg_id: int, top_k: int` | `list[dict]` | Busca trechos relevantes no ChromaDB via embeddings locais |

### Segurança do MCP

**Allowlist de operações:** O servidor expõe exatamente 4 tools, todas somente-leitura. Não há nenhuma tool de escrita, execução de comandos, acesso ao sistema de arquivos, ou chamada a APIs externas autenticadas além do Gutendex (público) e Wikipedia (público). O agente não pode criar, modificar ou deletar arquivos.

**Limitação de escopo:** O servidor opera exclusivamente sobre o corpus literário indexado no ChromaDB local. Não há acesso a outros bancos de dados, variáveis de ambiente sensíveis, ou recursos de rede além de `gutendex.com` e `en.wikipedia.org`.

**O que o agente não pode fazer via MCP:**
- Executar código arbitrário ou comandos do sistema
- Acessar ou modificar arquivos fora do ChromaDB
- Fazer chamadas a APIs autenticadas (ex.: OpenAI, LangSmith) — essas chamadas ocorrem diretamente no `LLMClient`, fora do MCP
- Buscar livros fora do domínio público (Gutenberg)
- Armazenar ou vazar dados do usuário

**Registro de chamadas:** Todas as invocações de tools são rastreadas via [LangSmith](https://smith.langchain.com/) através dos decorators `@traceable` no `LLMClient`. O nó `retriever` registra cada chamada MCP no trace do LangGraph (`on_chain_start` / `on_chain_end`), visível na UI do Streamlit e no dashboard do LangSmith.

**Justificativa de escolha e riscos:** O servidor MCP próprio foi escolhido (Opção 1 da spec) para encapsular o corpus literário como ferramenta padronizada, evitando acoplamento direto entre o grafo e a lógica de acesso a dados. O principal risco de supply-chain com servidores MCP de terceiros (exfiltração de dados, prompt injection via tool results) é mitigado pelo uso de um servidor local controlado. O único risco residual é o `get_book_philosophical_context`, que repassa dados da obra para o LLM — mitigado pelo fato de que os dados de entrada são públicos (Gutenberg) e a saída é apenas texto interpretativo, sem acesso a dados do usuário.

---

## Avaliação de Automação

A automação do LitGraph corresponde à rota `guide`, ativada quando o supervisor detecta a intenção de gerar um guia de estudo. O nó `automation` executa um workflow sequencial de 4 steps para produzir um documento estruturado com citações do texto original.

### Workflow de automação

```
retriever → automation → safety → answerer → self_check → output
```

O nó `automation` executa sempre os seguintes steps internos, rastreados em `automation_trace`:

| Step | Função | Descrição |
|------|--------|-----------|
| 1 | `build_study_plan` | Gera plano de leitura em 4–6 etapas adaptado ao nível do aluno |
| 2 | `extract_study_guide_elements` | Extrai personagens, temas, passagens-chave e perguntas de revisão |
| 3 | `build_revision_checklist` | Transforma o plano em checklist de 5–8 itens de revisão |
| 4 | `render_structured_study_guide` | Renderiza o guia final em português com 7 seções fixas |

## Avaliação RAG (RAGAS)

A avaliação seguiu o protocolo exigido na especificação do projeto: 10 perguntas rotuladas sobre obras do corpus (filosofia clássica e literatura russa), executadas contra o pipeline completo do LitGraph, com métricas calculadas via [RAGAS](https://docs.ragas.io).

A partir da terceira rodada (`rag_eval_0003`), o pipeline passou a usar o cache local de metadados (`static/data/book_cache.json`) em vez de buscar o Gutendex ao vivo, eliminando as falhas de indexação que afetavam metade das perguntas nas rodadas anteriores.

### Métricas — médias (subset `qa`, 10 perguntas)

| Métrica             | v1 (sem cache) | v2 (com cache) | Δ       | Interpretação                              |
|---------------------|:--------------:|:--------------:|:-------:|--------------------------------------------|
| `faithfulness`      | 0.6250         | **0.9417**     | +0.32   | Resposta está ancorada nos chunks?         |
| `answer_relevancy`  | 0.1518         | **0.1658**     | +0.01   | Resposta endereça diretamente a pergunta?  |
| `context_precision` | 0.0556         | **0.1622**     | +0.11   | Chunks recuperados são de fato relevantes? |
| `context_recall`    | 0.6944         | **0.7604**     | +0.07   | O contexto recuperado cobre o gabarito?    |

> **N por métrica (v2):** `faithfulness` = 8, `answer_relevancy` = 9, `context_precision` = 8, `context_recall` = 8.  

### Latência por pergunta (v2 — com cache)

| # | Pergunta | Latência (s) | Chunks |
|---|----------|:------------:|:------:|
| 1 | O que é a Alegoria da Caverna em A República de Platão? | 126,74 | 6 |
| 2 | Como Sócrates defende sua vida filosófica na Apologia de Platão? | 175,03 | 6 |
| 3 | O que é eudaimonia para Aristóteles na Ética a Nicômaco? | 184,63 | 6 |
| 4 | Como Aristóteles define o ser humano como animal político na Política? | 143,99 | 6 |
| 5 | Qual é o papel da memória nas Confissões de Agostinho? | 174,69 | 6 |
| 6 | Quais são as Cinco Vias de Tomás de Aquino para provar a existência de Deus? | 121,53 | 6 |
| 7 | Qual é a teoria de Raskolnikov sobre homens extraordinários em Crime e Castigo? | 163,34 | 6 |
| 8 | O que é o Grande Inquisidor em Os Irmãos Karamazov? | 83,87 | 6 |
| 9 | Qual é o papel do subterrâneo na filosofia do Homem do Subterrâneo de Dostoiévski? | 147,79 | 6 |
| 10 | Qual é a crise espiritual de Tolstói descrita em Uma Confissão? | 42,48 | 0 |
| — | **Média** | **136,41** | — |

> A pergunta 10 (Tolstói, *Uma Confissão*) ainda retorna 0 chunks — a obra está no corpus mas o safety-agent a classifica fora do escopo literário de ficção. As demais 9 perguntas foram respondidas com contexto completo.

### Análise dos resultados

**O que esta nos limitando:**
- **`answer_relevancy` persistentemente baixo (0.17):** o gargalo agora é o estilo das respostas — o answerer produz textos longos, estruturados em tópicos com disclaimers de evidência explícitos ("com base apenas nas evidências fornecidas…"). O RAGAS interpreta essa estrutura como baixa aderência à pergunta direta. Esse comportamento é uma escolha de design do self-check (anti-alucinação), não um bug.
- **Latência alta (~136 s em média):** o cache eliminou timeouts de rede, mas a latência base esta alta porque todas as perguntas chegam ao estágio de geração (antes 5 falhavam rápido). O gargalo é a inferência do LLM nas múltiplas chamadas por pergunta (normalize, answer, self-check, translate).
- **Pergunta 10 (Tolstói) ainda sem chunks:** a obra *A Confession* (ID 20203) está indexada, mas o supervisor a classifica como fora do escopo ao receber a query sem `book_title` explícito.

### Próximos passos para melhoria

- Ajustar o prompt do answerer para respostas mais diretas, reduzindo boilerplate de disclaimers que penalizam o `answer_relevancy`.
- Investigar a classificação da pergunta 10 — o supervisor pode estar roteando para `refuse` por "Confissão" parecer contexto religioso/espiritual e não literário.
- Reranker (ex.: `bge-reranker`) para melhorar `context_precision` além de 0.16.
- Ampliar o dataset para ≥ 20 perguntas para N mais robusto em todas as métricas.
- Enriquecer o prompt do usuario com mais informacao para ser utilizada no RAG nos livros e retornar informacoes mais relevantes para a pergunta dele.

## Avaliação de Automação

A automação do LitGraph corresponde à rota `guide`, ativada quando o supervisor detecta a intenção de gerar um guia de estudo. O nó `automation` executa um workflow sequencial de 4 steps para produzir um documento estruturado com citações do texto original.

### Workflow de automação

```
retriever → automation → safety → answerer → self_check → output
```

O nó `automation` executa sempre os seguintes steps internos, rastreados em `automation_trace`:

| Step | Função | Descrição |
|------|--------|-----------|
| 1 | `build_study_plan` | Gera plano de leitura em 4–6 etapas adaptado ao nível do aluno |
| 2 | `extract_study_guide_elements` | Extrai personagens, temas, passagens-chave e perguntas de revisão |
| 3 | `build_revision_checklist` | Transforma o plano em checklist de 5–8 itens de revisão |
| 4 | `render_structured_study_guide` | Renderiza o guia final em português com 7 seções fixas |

### Tarefas avaliadas

| # | Tarefa | Nível | Sucesso | Steps | Lat (s) | Obs |
|---|--------|-------|:-------:|:-----:|:-------:|-----|
| 1 | Guia d'A República de Platão | superior | ✓ | 4 | 284,26 | — |
| 2 | Guia da Ética a Nicômaco de Aristóteles | fundamental | ✗ | 0 | 18,72 | Falha no retriever¹ |
| 3 | Guia de Assim Falou Zaratustra (Nietzsche) | médio | ✓ | 4 | 285,95 | — |
| 4 | Guia d'Os Irmãos Karamazov (Dostoiévski) | superior | ✓ | 4 | 362,00 | — |

### Métricas de automação

| Métrica | Valor |
|---------|-------|
| Taxa de sucesso | 3/4 (75%) |
| Steps médios | 3,0 |
| Latência média | 237,73 s |

> ¹ **Tarefa 2 — falha no retriever, não na automação.** A Ética a Nicômaco falhou com 0 steps em 18 s — o pipeline interrompeu antes de chegar ao nó `automation`. O `book_title` do dataset (`"Nicomachean Ethics"`) diverge do título registrado no Gutenberg (`"The Ethics of Aristotle by Aristotle"`), causando erro de lookup no cache e roteamento para `refuse`. As 3 tarefas bem-sucedidas completaram todas as 4 etapas do workflow sem falha.

## Stack e decisões técnicas

### LLM — OpenAI em vez de Ollama local

A especificação do projeto sugere o uso de modelos open-source via Ollama (Llama 3.x, Qwen2.5, Mistral etc.) como preferência. O LitGraph utiliza a API da OpenAI (`gpt-5-mini`)por uma limitação de infraestrutura: o corpus do projeto inclui obras densas de filosofia clássica e literatura russa em inglês, e as chamadas encadeadas do pipeline (normalize → answer → self-check → translate) exigem um modelo com forte capacidade de reasoning e seguimento de instruções em múltiplos idiomas. Rodar um modelo local com esse nível de qualidade exigiria hardware com GPU dedicada (mínimo 16 GB VRAM para modelos 13B+), o que não estava disponível no ambiente de desenvolvimento.

Os embeddings, no entanto, rodam inteiramente local via `sentence-transformers` (`all-MiniLM-L6-v2`, HuggingFace), conforme exigido pela spec — nenhuma chamada externa (com excessao das chamadas para o gutendex) é feita na etapa de indexação ou recuperação de chunks.