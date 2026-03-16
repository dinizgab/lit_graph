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

### Métricas — médias (subset `qa`, 10 perguntas)

| Métrica             | Valor  | Interpretação                              |
|---------------------|--------|--------------------------------------------|
| `faithfulness`      | 0.6250 | Resposta está ancorada nos chunks?         |
| `answer_relevancy`  | 0.1518 | Resposta endereça diretamente a pergunta?  |
| `context_precision` | 0.0556 | Chunks recuperados são de fato relevantes? |
| `context_recall`    | 0.6944 | O contexto recuperado cobre o gabarito?    |

> **N por métrica:** `faithfulness` = 3, `answer_relevancy` = 8, `context_precision` = 3, `context_recall` = 3.  
> O N reduzido em algumas métricas reflete perguntas para as quais o pipeline não conseguiu recuperar contexto (0 chunks), tornando o cálculo inviável pelo RAGAS.

### Latência por pergunta

| # | Pergunta | Latência (s) | Chunks |
|---|----------|:------------:|:------:|
| 1 | O que é a Alegoria da Caverna em A República de Platão? | 36,33 | 0 |
| 2 | Como Sócrates defende sua vida filosófica na Apologia de Platão? | 187,15 | 6 |
| 3 | O que é eudaimonia para Aristóteles na Ética a Nicômaco? | 12,28 | 0 |
| 4 | Como Aristóteles define o ser humano como animal político na Política? | 8,59 | 0 |
| 5 | Qual é o papel da memória nas Confissões de Agostinho? | 48,02 | 0 |
| 6 | Quais são as Cinco Vias de Tomás de Aquino para provar a existência de Deus? | 145,49 | 6 |
| 7 | Qual é a teoria de Raskolnikov sobre homens extraordinários em Crime e Castigo? | 182,64 | 6 |
| 8 | O que é o Grande Inquisidor em Os Irmãos Karamazov? | 123,71 | 6 |
| 9 | Qual é o papel do subterrâneo na filosofia do Homem do Subterrâneo de Dostoiévski? | 191,36 | 6 |
| 10 | Qual é a crise espiritual de Tolstói descrita em Uma Confissão? | 43,74 | 0 |
| — | **Média** | **97,93** | — |

### Análise dos resultados

**O que funcionou bem:**
- O `context_recall` de 0.69 indica que, quando o sistema consegue indexar a obra, os chunks recuperados cobrem bem o conteúdo esperado pela resposta de referência.
- O `faithfulness` de 0.63 mostra que o answerer respeita as evidências recuperadas — o mecanismo de self-check está cumprindo seu papel de ancoragem.
- Nas perguntas com 6 chunks (Dostoiévski, Aquino, Sócrates), o pipeline produziu respostas estruturadas e com citações do texto original.

**Limitações identificadas:**
- **`answer_relevancy` baixo (0.15):** as respostas são longas, estruturadas em tópicos e com disclaimers de evidência — o RAGAS interpreta isso como baixa aderência à pergunta. A postura conservadora do self-check (recusar quando evidências são insuficientes) é desejável como comportamento, mas penaliza a métrica.
- **`context_precision` muito baixo (0.06):** os chunks recuperados incluem ruído (sumários, índices, trechos periféricos). Um reranker ou filtragem semântica mais fina reduziria esse problema.
- **Falhas de indexação (5 de 10 perguntas com 0 chunks):** metade das perguntas resultou em erro de busca no Gutendex — timeout de rede, títulos não encontrados pela busca literal (ex.: `"Nicomachean Ethics"` vs. `"The Ethics of Aristotle"`) ou obras classificadas fora do escopo pelo safety-agent.

### Próximos passos para melhoria

- Cache local das obras já indexadas para eliminar re-downloads e reduzir latência.
- Normalização de título com fuzzy matching ou lookup por Gutenberg ID direto para reduzir falhas de busca.
- Reranker (ex.: `bge-reranker`) para melhorar `context_precision`.
- Ampliar o dataset para ≥ 20 perguntas com cobertura de obras que o sistema indexa com sucesso.
- Ajustar o prompt do answerer para respostas mais diretas, reduzindo boilerplate de disclaimers.