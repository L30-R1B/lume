# Matriz de requisitos — estado verificável

Estados: **pendente**, **implementado**, **validado**, **bloqueado**, **não aplicável**. Validado limita-se ao comportamento/fixture apontado. Uma seção não está concluída se alguma obrigação nela segue pendente. Estado global: **escopo incompleto**. Este documento não transforma mecanismos parciais em produto aprovado.

| ID | Requisito | Estado | Implementação / verificação / evidência ou lacuna |
|---|---|---|---|
| R01.01 | Inspeção Linux, recursos, ferramentas, Codex/auth/config | validado | doctor.json; Codex 0.166.0, ChatGPT, modelo existente |
| R01.02 | PDFs exigidos | bloqueado | nomes exatos ausentes na busca documentada; não lidos |
| R01.03 | Fontes oficiais/licenças | validado | research.md; docs oficiais; licenças nos pacotes |
| R01.04 | Repositório dedicado sem alterar projetos alheios | validado | /home/leo-ribeiro/codex-economy; fixtures próprias |
| R02.01 | CLI humana/JSON e todas funções básicas | implementado | CLI com register/index/search/read/graph/impact/run/session/task/metrics/benchmark/export/prune/backup/restore/doctor |
| R02.02 | MCP local e catálogo pequeno | validado | seis tools; teste SDK stdio; chamada real em codex-mcp-approved.jsonl |
| R02.03 | Integração com login ChatGPT | validado | smoke real e MCP; sem leitura/reutilização OAuth |
| R02.04 | Perfil reversível e preservação config | validado | profile-lifecycle.json confirma remoção/reinstalação/idempotência e hash da configuração principal preservado |
| R02.05 | Skills/instruções específicas por projeto | pendente | skill curta fornecida; instalador de extensões por projeto falta |
| R02.06 | Hooks úteis compatíveis | não aplicável | eventos exec usados; nenhum hook necessário ao caminho atual; telemetria adicional não implementada |
| R02.07 | Contratos/schema/discovery | implementado | CLI doctor; SDK MCP; schemas app-server gerados pelo binário; validação automática contra schemas pendente |
| R03.01 | SQLite persistente, FTS, símbolos, grafo | validado | store/engine; testes de consulta e integridade |
| R03.02 | Snapshots/worktrees/arquivos atuais não commitados | implementado | raiz+HEAD+conteúdo; teste branches/worktrees completo pendente |
| R03.03 | Contratos/documentos/testes/alvos como entidades específicas | pendente | arquivos/símbolos/commands existem; entidades e relações de build completas faltam |
| R03.04 | Fatos com origem/local/status | implementado | symbols/edges; local completo compilador em events; granularidade de edges ainda por arquivo |
| R03.05 | Identidade em renome e deslocamento | implementado | preserva file id para renome por hash único; symbol id por file/kind/name/ocorrência; teste específico |
| R03.06 | Hashes/cache incremental | validado | incremental altera/renomeia/exclui; cache determinístico |
| R03.07 | Invalidação dependências/config/versões | implementado | relações reconstruídas; fingerprint inclui arquivos, versões e compile_commands; testes adicionais pendentes |
| R03.08 | Concorrência e transação recuperável | validado | múltiplos writers, rollback de extrator; segunda varredura; cancelamento real indexação pendente |
| R03.09 | Estado incompleto/obsoleto explícito | validado | ready/partial/stale/missing; omissões e erro de freshness |
| R04.01 | JS/TS símbolos/imports | validado | Tree-sitter fixtures e benchmark Node |
| R04.02 | JS/TS aliases/referências semânticas | validado | Compiler API 5.9.3 com tsconfig paths; test_compilers |
| R04.03 | Next contratos de framework | pendente | TS/JS genéricos funcionam; rotas/server-client/actions não modeladas |
| R04.04 | Prisma e SQL | implementado | modelos/tabelas inferidos; migração SQLite real; sem Prisma CLI/contratos completos |
| R04.05 | Python estrutura/imports/referências | implementado | AST/imports/calls inferidos; não resolução semântica global; benchmark real Python |
| R04.06 | Kotlin estrutura e compilação | implementado | Tree-sitter; compiler 2.4.21 instalado e fixture JVM executada |
| R04.07 | Android/Gradle módulos/recursos/gerados/dependências | pendente | comandos Gradle descobertos; análise Android/Gradle integral e alteração validada faltam |
| R04.08 | C/C++ configuração real/referências | validado | libclang 18.1.1 usa banco CMake; alteração/build/exec em test_compilers |
| R04.09 | CMake/CTest alvos/testes representados | implementado | descoberta de comandos e CTest real no benchmark; codemodel de alvos falta |
| R04.10 | Docker/Compose/infra | implementado | Compose YAML services/depends_on declarados; demais manifests e validação Docker real pendentes |
| R04.11 | Contrato extensível/capacidades por projeto | pendente | adapters.extract modular; falta registro e relatório completo de capacidades |
| R04.12 | Tecnologias desconhecidas/projeto novo | validado | inventário/texto/leitura; busca insuficiente explícita quando vazia |
| R05.01 | Literal/estrutural/híbrido/full/assisted | implementado | engine.search/context; benchmark compara A/B/C; modos testados parcialmente |
| R05.02 | Expansão seletiva grafo e recuperação iterativa | implementado | graph separado com limites; incorporação progressiva ao contexto falta |
| R05.03 | Semântica/reranking substituíveis | implementado | Protocols; reranker TF-IDF local funcional; sem neural semantics |
| R05.04 | Fonte fiel/hash/posições/omissões/origem/testes | implementado | pacote original fiel; enriquecimento automático de interfaces/testes falta |
| R05.05 | Mapas hierárquicos/resumos rastreáveis | implementado | ce map retorna hierarquia determinística caminho/símbolo/posição/hash; sem resumos gerados |
| R05.06 | SWE-Pruner/LongCodeZip/LLMLingua experimental | pendente | princípio de seleção fiel; integrações experimentais distintas faltam |
| R05.07 | Internals de modelo fechado | não aplicável | sem acesso a pesos/KV/representações/observation masking exato; nenhum controle simulado |
| R06.01 | Jev API/schema/Choice/Score/Noul | implementado | docs oficiais; batch real no código; fake explícito em testes |
| R06.02 | Jev real autenticado | bloqueado | TYPESAFE_API_KEY não disponibilizada no ambiente; arquivos pessoais não usados como cofre presumido |
| R06.03 | Calibração em dados separados | pendente | não há decisão de parada/aceite baseada em limiar arbitrário |
| R06.04 | Bypass/off/fallback/erros classificados | validado | testes chave ausente, política, fake, timeout, inválido; erros HTTP adicionais pendentes |
| R06.05 | Entrada/timeout/concorrência/cache inferência | implementado | limites de entrada/timeout/uma tentativa; controle global concorrente/cache inferência faltam |
| R06.06 | Telemetria auxiliar/modelo/uso/latência | implementado | events com resposta usada/modelo/usage/latência; custo nulo sem billing |
| R06.07 | Privacidade/chaves/política externa | implementado | env; external=false; limites/redação; análise completa de segredos pendente |
| R06.08 | Auxiliar adicional offline funcional | validado | TF-IDF char 3–5/max30k; teste ranking; nenhuma rede no algoritmo |
| R07.01 | Saída causal/exit/stderr integral limitada/expansão | validado | runner; log; teste 3000 linhas/multibyte/exit7 |
| R07.02 | Formatos estruturados/agrupamento duplicados | pendente | logs preservados; sumarização por linhas; parser estrutural e contagem duplicados faltam |
| R07.03 | Ferramentas determinísticas e batch dependências | implementado | argv/CMake/CTest/npm/Python; batch DAG falta |
| R07.04 | Timeout/cancelamento/subprocessos/limites | validado | timeout e grupo de processos; output limit; limites CPU/RAM pendentes |
| R07.05 | Argumentos seguros sem shell | validado | injeção $(...) não executada; teste runner |
| R08.01 | Estado objetivo/aceite/snapshot/decisões/checks | implementado | sessions + CLI/handoff MCP; teste retomada longa falta |
| R08.02 | Cache separado de extração/inferência/tarefa | pendente | namespace extraction ativo; namespaces adicionais sem políticas/uso |
| R08.03 | Ações repetidas/evidência válida | implementado | consultas equivalentes por fingerprint/modo/termos geram aviso persistente; reset por alteração de fonte testado; ações de execução ainda não deduplicadas |
| R08.04 | Roteamento de documentos/continuidade por utilidade | pendente | handoff manual disponível; política automática falta |
| R09.01 | Preparação/Codex/eventos/verificação/resultado | implementado | orchestrator + runner; benchmark altera/checks reais; aceite task exige verificação independente |
| R09.02 | Modelos/esforço/orçamento distinguido | implementado | task flags + bytes/output/task timeout; sem teto global de tokens |
| R09.03 | Delegação configurável contabilizada | pendente | nenhuma delegação automática usada |
| R09.04 | Continuação/bloqueio sem falso sucesso | implementado | task permanece active/blocked; benchmark preserva erros e retomada; budget global falta |
| R10.01 | Inputs/erros/validação config/diagnóstico | implementado | CLI JSON errors; políticas validadas; validação integral de contratos falta |
| R10.02 | Migração real entre schemas | pendente | criação schema1 transacional e rejeição versões; sem versão2 testada |
| R10.03 | Segurança traversal/symlinks/binários/multibyte | validado | test_boundaries; O_NOFOLLOW, UTF-8 estrito; auditoria não independente |
| R10.04 | Retenção/logs/redação | implementado | prune/eventos/logs; coleta snapshots/cache e regras mais completas faltam |
| R10.05 | Backup/restore/corrupção | implementado | backup real íntegro; restore saudável validado em restore-check.json; restauração de corrupção integral pendente |
| R10.06 | Instalação fora checkout/build/update | implementado | runtime próprio instalado e testado em /tmp; wheel/sdist gerados |
| R10.07 | Desinstalação preserva projetos/config/credenciais | validado | installation-cycle.json e profile-lifecycle.json; estado e projetos preservados; toolchains opcionais permanecem no prefixo |
| R10.08 | Serviço/exposição explícita | validado | stdio sob demanda; nenhuma porta/daemon; serviço permanente não necessário |
| R11.01 | Suíte comportamental famílias e fronteiras | implementado | 16 testes + evidências; Android/Next/infra completos faltam |
| R11.02 | Build/lint/auditoria | validado | build.txt; lint.txt; dependency-audit.json após pip26.3 sem CVEs conhecidos |
| R11.03 | Performance fria/incremental/buscas/DB/RAM | validado | 600 arquivos/3 projetos, performance.json, gates específicos passados |
| R11.04 | Branch/worktrees/falhas parciais/cancelamento | pendente | cobertura não integral; rollback e concorrência testados |
| R12.01 | Executor benchmark A/B/C isolado/retomável | implementado | benchmark.py; manifest; raw results.jsonl/events/patches |
| R12.02 | D Jev e E técnicas avançadas comparadas | bloqueado | D sem chave; E distinto ainda não implementado |
| R12.03 | 12 tarefas/3 famílias/3 repetições/arm | pendente | 108 jobs A/B/C iniciados; execução ainda em andamento |
| R12.04 | Piloto separado/congelamento/holdout | pendente | avaliação atual exploratória: formatter alterou whitespace de fixtures durante jobs; conservar dados, não tratar como confirmação final |
| R12.05 | Tokens reais/cache/output/reasoning sem dupla contagem | implementado | exec JSON usage; total input+output; cached subset separado; reasoning apenas informado |
| R12.06 | Todas tentativas/aceite/regressões/amortização | implementado | falhas conservadas; taxa e tokens/aceita; regressões maiores/amortização/releituras detalhadas faltam |
| R12.07 | Pareamento/incerteza/consumo assinatura | implementado | bootstrap de pares disponíveis; contador assinatura indisponível; confirmação completa falta |
| R12.08 | Meta >=80% | pendente | inconclusiva; nenhum percentual de pacote usado como economia total |
| R13.01 | Rastreabilidade pesquisas | implementado | research.md explícito sobre ausências, equivalências e não aplicáveis |
| R13.02 | Documentação consistente/RC/evidências | implementado | README/operations/research/requirements/checkpoint; não há aprovação de produção |

Não atribuímos pendências de implementação a bloqueios externos. Apenas PDFs ausentes e credencial Jev ausente são bloqueios externos identificados. As demais pendências são trabalho ainda necessário.
