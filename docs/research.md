# Pesquisa e escolhas verificáveis

Não foram encontrados pelo nome exato, em busca recursiva no diretório pessoal com exclusão de caches/dependências e cópias de CI:

- Codex_Economia_Tokens_Pesquisa_2026-11-04.pdf
- Codex_Grafos_Indices_Modelos_Leves_Estudos_Internacionais.pdf

Não foram lidos; a rastreabilidade de recomendações específicas e referências internas desses PDFs está bloqueada pela ausência. As linhas abaixo rastreiam os requisitos explícitos e fontes consultadas, sem atribuir conteúdo aos PDFs.

| Mecanismo | Implementação/política | Teste/evidência | Estado |
|---|---|---|---|
| Recuperação sob demanda, BM25, símbolos | engine.search; lexical antes de híbrido/assisted | test_incremental; MCP real | validado |
| AST e parsers maduros | Python ast e Tree-sitter; fatos sintáticos não são resolução semântica | test_adapters | validado |
| Compiladores/aliases | semantic, TS 5.9.3 e libclang/banco CMake | test_compilers; ts-semantic.json; cpp-semantic.json | validado nas fixtures |
| SCIP/LSP | Alternativas ao compilador; não incorporadas | — | não aplicável à implementação atual; cobertura extra pendente |
| Grafo, vizinhança e impacto | engine.graph, limites de direção/tipo/profundidade | test_adapters (limite); teste de impacto profundo pendente | implementado |
| Hashes/invalidação | fingerprint de conteúdo/política/HEAD, segunda leitura transacional | test_incremental; rollback; concorrência | validado parcialmente |
| Mapas hierárquicos, roteamento de docs | ce map retorna caminhos/símbolos/hashes; roteamento temático automático falta | test_repetition_resets_on_source_change_and_map | implementado parcialmente |
| Reranking local | TF-IDF caracteres ajustado por corpus; sem pesos externos; não é semântica neural | test_jev_mock_and_local; híbrido no benchmark | validado como reranker |
| Embeddings e reranking locais | TF-IDF e LSA sem rede; contrato substituível | testes comportamentais | validado localmente; não equivale a embedding neural |
| Jev: relevância/action/repetição | Um batch de Scores, Choice e Noul; somente ordenação usada | fake controlado, timeout e cinco chamadas reais em fixture sintética; `evidence/jev-ranking-real.json` | validado no serviço em escopo limitado; comparação D bloqueada por custos |
| JevCoder | Princípio de julgamento atômico e decisões em código; não reproduzido integralmente | providers; nenhuma alegação dos resultados do artigo | implementado parcialmente |
| Refinamento/localização separada da edição | MCP leitura/busca, task executa edição separada | MCP real; benchmark | implementado |
| Testes/traces/evidência dinâmica | Runner preserva exit/stderr e permite expansão; trace Python registra chamadas observadas por snapshot | testes do runner e trace | validado nas fixtures, não universal |
| Seleção fiel e arquivos completos | trechos originais com hash/linhas, orçamento de bytes, omissões | test_budgets | validado |
| SWE-Pruner/LongCodeZip/LLMLingua | Seleção fiel é princípio transferível; LLMLingua-2 opcional isolado para documentos, sem equivalência declarada | `evidence/neural-offline-enforced.json` | validado em exemplo documental; não medido como economia por tarefa |
| SWE-Pruner Pro/internal representations | Requer acesso interno não exposto pelo Codex fechado | limites oficiais | não aplicável |
| Quantização, KV cache, fine-tuning, destilação | Não expostos pelo harness do Codex autenticado | nenhum controle falso implementado | não aplicável |
| Filtragem de resultados | seleção causal começo/erro/final; recuperação por linhas | runner multibyte, saída extensa | validado |
| Execução programática | argv, timeout, grupo de processos; sem shell implícito | runner; testes CMake reais | validado parcialmente |
| Memória/handoff | sessions guarda objetivo/aceite/decisões/checks e próximo passo | validação de continuidade longa pendente | implementado |
| Masking/compactação | Não há controle exato de histórico via MCP/exec; handoff é alternativa | doctor declara falso | masking não aplicável; política automática pendente |
| Cache | extração hash/versionada, inferência com modelo fixo e resultados de tarefa com validação | testes incrementais e operações | implementado; validade depende do snapshot |
| Skills progressivas | skill curta instalada por `ce setup` no projeto autorizado, remoção preserva arquivos editados | `evidence/release-validation.json` | validado em projeto isolado |
| Catálogo pequeno | seis ferramentas MCP stdio | teste cliente + Codex real | validado |
| Aceite/esforço/modelo | task parametriza; benchmark verifica testes protegidos; não aceita só pelo juiz | eventos/fixtures | implementado parcialmente |
| Delegação | configuração explícita, worktrees isoladas e contabilização; desligada por padrão | testes locais, sem execução multiagente real | implementado; validação real pendente |
| Avaliação pareada | fila retomável, tentativas brutas, input/output/cache, bootstrap agrupado por problema | `evidence/editor-confirmation-r2/`, `evidence/confirmation-v2/` | validado em tarefas pequenas; confirmação abrangente e braço D pendentes |

Fontes primárias consultadas em 2026-11-04:

- https://learn.chatgpt.com/docs/extend/mcp — stdio, catálogo e modos de aprovação por servidor/ferramenta.
- https://learn.chatgpt.com/docs/app-server — integração oficial; schema também gerado pelo binário 0.166.0.
- https://learn.chatgpt.com/docs/config-file/config-reference — configuração compatível com a versão em uso.
- https://docs.typesafe.ai/introduction e https://docs.typesafe.ai/introduction/quickstart — endpoint HTTPS, autorização Bearer, schema e consumo.
- https://docs.typesafe.ai/primitives/choice, /score, /noul e /confidence — probabilidade e confidence têm significados distintos. Não foram calibrados limiares em conjunto externo; por isso não há decisão automática de aceite/stop.
- https://arxiv.org/abs/2610.19596 — JevCoder, referência conceitual. Resultados publicados não são resultados deste produto.
- https://github.com/jcressler/jev-codex-token-saver — seleção delimitada, bypass e fallback; referência MIT, nenhum código copiado.
- https://tree-sitter.github.io/tree-sitter/ — parsing incremental e limites de estrutura.
- https://www.sqlite.org/fts5.html — FTS5/BM25 e integridade.
- https://github.com/microsoft/TypeScript/wiki/Using-the-Compiler-API — API legada anterior à versão 7; versão 5.9.3 fixada.
- https://clang.llvm.org/docs/JSONCompilationDatabase.html — configuração real por unidade de compilação.
- https://kotlinlang.org/docs/command-line.html — compilador Kotlin 2.4.21 e execução JVM.
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports — MCP stdio, stdout reservado ao protocolo.

Licenças: código próprio MIT; mcp/PyYAML/parsers Tree-sitter MIT; SQLite domínio público; scikit-learn BSD-3-Clause; TypeScript e Kotlin Apache-2.0; libclang Apache-2.0 com exceção LLVM. Pacotes distribuídos pelos respectivos gerenciadores preservam seus arquivos de licença. Não incorporamos RTK, SCIP ou código dos artigos. Inventário instalado está em requirements.lock e requirements-runtime.lock; auditoria em evidence/dependency-audit.json.
