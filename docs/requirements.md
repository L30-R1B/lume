# Matriz de requisitos — estado verificável

Estados: **pendente**, **implementado**, **validado**, **bloqueado**, **não aplicável**. Validado limita-se ao comportamento/fixture apontado. Uma seção não está concluída se alguma obrigação nela segue pendente. Estado global: **escopo incompleto**. Este documento não transforma mecanismos parciais em produto aprovado.

| ID | Requisito | Estado | Implementação / verificação / evidência ou lacuna |
|---|---|---|---|
| R01.01 | Inspeção Linux, recursos, ferramentas, Codex/auth/config | validado | doctor.json; Codex 0.166.0, ChatGPT, modelo existente |
| R01.02 | PDFs exigidos | bloqueado | Ambos PDFs de nomes exatos ausentes; recomendações internas não foram atribuídas. |
| R01.03 | Fontes oficiais/licenças | validado | research.md; docs oficiais; licenças nos pacotes |
| R01.04 | Repositório dedicado sem alterar projetos alheios | validado | Repositório Lume; fixtures próprias em tests/ |
| R02.01 | CLI humana/JSON e todas funções básicas | implementado | CLI inclui registro, índices, contexto, sessões, métricas, benchmark, backup, recuperação e manutenção. |
| R02.02 | MCP local e catálogo pequeno | validado | seis tools; teste SDK stdio; chamada real em codex-mcp-approved.jsonl |
| R02.03 | Integração com login ChatGPT | validado | smoke real e MCP; sem leitura/reutilização OAuth |
| R02.04 | Perfil reversível e preservação config | validado | profile-lifecycle.json confirma remoção/reinstalação/idempotência e hash da configuração principal preservado |
| R02.05 | Skills/instruções específicas por projeto | validado | setup instala/remove skill própria; testes de idempotência e symlink; hooks opcionais têm revisão de confiança do Codex. |
| R02.06 | Hooks úteis compatíveis | validado | Hook local observado em projeto descartável com confiança temporária oficial para a definição inspecionada; operação normal exige trust. |
| R02.07 | Contratos/schema/discovery | validado | Schemas app-server gerados e usados para validar pedidos; integração real documentada. |
| R03.01 | SQLite persistente, FTS, símbolos, grafo | validado | store/engine; testes de consulta e integridade |
| R03.02 | Snapshots/worktrees/arquivos atuais não commitados | validado | Teste de branches e worktree; conteúdo, raiz e HEAD fazem parte do snapshot. |
| R03.03 | Contratos/documentos/testes/alvos como entidades específicas | validado | Entidades de testes, documentos, schemas, serviços, contratos, alvos CMake e módulos Gradle. |
| R03.04 | Fatos com origem/local/status | implementado | symbols/edges; local completo compilador em events; granularidade de edges ainda por arquivo |
| R03.05 | Identidade em renome e deslocamento | validado | Teste preserva identidade em renome com hash único e deslocamento; edição+renome e sobrecargas reordenadas limitados. |
| R03.06 | Hashes/cache incremental | validado | incremental altera/renomeia/exclui; cache determinístico |
| R03.07 | Invalidação dependências/config/versões | implementado | relações reconstruídas; fingerprint inclui arquivos, versões e compile_commands; testes adicionais pendentes |
| R03.08 | Concorrência e transação recuperável | validado | Concorrência, falha e SIGINT real; transação revertida e retomada testadas. |
| R03.09 | Estado incompleto/obsoleto explícito | validado | ready/partial/stale/missing; omissões e erro de freshness |
| R04.01 | JS/TS símbolos/imports | validado | Tree-sitter fixtures e benchmark Node |
| R04.02 | JS/TS aliases/referências semânticas | validado | Compiler API 5.9.3 com tsconfig paths; test_compilers |
| R04.03 | Next contratos de framework | validado | Rotas por convenção marcadas inferidas; Next real compila e responde antes/depois. |
| R04.04 | Prisma e SQL | validado | Prisma valida schema e gera SQL; SQLite executa migração antes/depois; parsing de contratos continua heurístico. |
| R04.05 | Python estrutura/imports/referências | validado | Python AST e Jedi reais, chamadas observadas via sys.setprofile e teste de alteração. |
| R04.06 | Kotlin estrutura e compilação | implementado | Tree-sitter; compiler 2.4.21 instalado e fixture JVM executada |
| R04.07 | Android/Gradle módulos/recursos/gerados/dependências | validado | Gradle real, APK Android API 36, teste unitário e recurso alterado conferido no APK; sem teste em dispositivo. |
| R04.08 | C/C++ configuração real/referências | validado | libclang 18.1.1 usa banco CMake; alteração/build/exec em test_compilers |
| R04.09 | CMake/CTest alvos/testes representados | validado | CMake File API e CTest JSON representam alvos e testes. |
| R04.10 | Docker/Compose/infra | validado | Compose config real antes/depois, YAML seguro e entidades de manifests; sem alegar execução de containers. |
| R04.11 | Contrato extensível/capacidades por projeto | implementado | Contrato de entry point de adaptador e relatório por projeto; extensões externas não auditadas. |
| R04.12 | Tecnologias desconhecidas/projeto novo | validado | inventário/texto/leitura; busca insuficiente explícita quando vazia |
| R05.01 | Literal/estrutural/híbrido/full/assisted | implementado | engine.search/context; benchmark compara A/B/C; modos testados parcialmente |
| R05.02 | Expansão seletiva grafo e recuperação iterativa | validado | Expansão bounded por tipos e refino direcionado; testes de orçamento e origem. |
| R05.03 | Semântica/reranking substituíveis | implementado | Protocols; reranker TF-IDF local funcional; sem neural semantics |
| R05.04 | Fonte fiel/hash/posições/omissões/origem/testes | implementado | Fonte original, hashes, relações, testes e omissões; cobertura de invariantes depende da recuperação. |
| R05.05 | Mapas hierárquicos/resumos rastreáveis | implementado | ce map retorna hierarquia determinística caminho/símbolo/posição/hash; sem resumos gerados |
| R05.06 | SWE-Pruner/LongCodeZip/LLMLingua experimental | validado | Variantes fiéis isoladas e LLMLingua-2 real offline para documentos; sem alegar equivalência a papers ou comprimir código. |
| R05.07 | Internals de modelo fechado | não aplicável | sem acesso a pesos/KV/representações/observation masking exato; nenhum controle simulado |
| R06.01 | Jev API/schema/Choice/Score/Noul | validado | Choice, Score e Noul por Jev real 1.14.0; fallback e testes controlados separados. |
| R06.02 | Jev real autenticado | validado | Chave fornecida pelo usuário; requisição real e seleção real de evidências, modelo e uso registrados. |
| R06.03 | Calibração em dados separados | validado | 24 rótulos sintéticos para calibração e 8 separados para avaliação; domínio restrito a definição de função. |
| R06.04 | Bypass/off/fallback/erros classificados | validado | Testes de bypass, off, política, chave, timeout, resposta inválida, limite e HTTP 429. |
| R06.05 | Entrada/timeout/concorrência/cache inferência | validado | Limites de entrada, duas vagas de concorrência e cache apenas em versão fixada. |
| R06.06 | Telemetria auxiliar/modelo/uso/latência | validado | Evento real registra modelo, tokens, latência, decisão e modo; custo efetivo de conta indisponível. |
| R06.07 | Privacidade/chaves/política externa | implementado | Chave 0600 fora de logs; projeto precisa permitir envio; cobrança adicional desativada por padrão. |
| R06.08 | Auxiliar adicional offline funcional | validado | TF-IDF char 3–5/max30k; teste ranking; nenhuma rede no algoritmo |
| R07.01 | Saída causal/exit/stderr integral limitada/expansão | validado | runner; log; teste 3000 linhas/multibyte/exit7 |
| R07.02 | Formatos estruturados/agrupamento duplicados | validado | Agrupamento de mensagens repetidas e campos JSON estruturados; conteúdo redigido expansível. |
| R07.03 | Ferramentas determinísticas e batch dependências | validado | Batch DAG testa ordem de dependências, falhas e paralelismo limitado. |
| R07.04 | Timeout/cancelamento/subprocessos/limites | validado | Timeout, grupo de processos, limite de saída e limites opcionais de CPU/RAM Linux testados. |
| R07.05 | Argumentos seguros sem shell | validado | injeção $(...) não executada; teste runner |
| R08.01 | Estado objetivo/aceite/snapshot/decisões/checks | validado | Sessões e handoff preservados; aceite exige runs reais após sessão com fingerprint atual. |
| R08.02 | Cache separado de extração/inferência/tarefa | validado | Extração por hash/versão; inferência por modelo fixado/TTL; resultado de tarefa exige fingerprint e novos checks. |
| R08.03 | Ações repetidas/evidência válida | implementado | consultas equivalentes por fingerprint/modo/termos geram aviso persistente; reset por alteração de fonte testado; ações de execução ainda não deduplicadas |
| R08.04 | Roteamento de documentos/continuidade por utilidade | implementado | Roteamento por assunto e continuidade por estado/orçamento; heurísticas não garantem suficiência. |
| R09.01 | Preparação/Codex/eventos/verificação/resultado | validado | Codex real altera código, verifica independentemente e atualiza índice; app-server validado por eventos reais. |
| R09.02 | Modelos/esforço/orçamento distinguido | implementado | task flags + bytes/output/task timeout; sem teto global de tokens |
| R09.03 | Delegação configurável contabilizada | validado | Duas tarefas independentes executadas em worktrees por Codex real; verificações, isolamento e 192.975 tokens registrados; desabilitado por padrão. |
| R09.04 | Continuação/bloqueio sem falso sucesso | validado | Sessões bloqueadas não podem ser aceitas; interrupção app-server observada e retomada de fila sem sobrescrita. |
| R10.01 | Inputs/erros/validação config/diagnóstico | implementado | Config versionada por schema JSON, modo estruturado, diagnóstico; todos subprocessos mantêm estado e código. |
| R10.02 | Migração real entre schemas | validado | Migrações transacionais 1→2→3 e persistência em registros legados testadas; banco instalado verificado. |
| R10.03 | Segurança traversal/symlinks/binários/multibyte | validado | test_boundaries; O_NOFOLLOW, UTF-8 estrito; auditoria não independente |
| R10.04 | Retenção/logs/redação | implementado | Retenção e redação; bytes inválidos preservados em saídas redigidas novas, dados anteriores ao schema 3 ou além do limite não são recuperáveis. |
| R10.05 | Backup/restore/corrupção | validado | Backup e restauração de corrupção testados; arquivos anteriores preservados; bundle valida checksums e travessia. |
| R10.06 | Instalação fora checkout/build/update | validado | Atualização instalada e validação isolada de 10 operações de instalação, upgrade, rollback e remoção. |
| R10.07 | Desinstalação preserva projetos/config/credenciais | validado | release-schema3-latest.json; estado e projeto preservados, configuração pessoal não substituída. |
| R10.08 | Serviço/exposição explícita | validado | stdio sob demanda; nenhuma porta/daemon; serviço permanente não necessário |
| R11.01 | Suíte comportamental famílias e fronteiras | implementado | 46 testes passaram e provas reais cobrem fixtures; não demonstram todos os cenários nem Android em dispositivo. |
| R11.02 | Build/lint/auditoria | validado | Build/lint passaram; pip-audit sem vulnerabilidades conhecidas nas 47 dependências runtime; npm audit anterior zero. |
| R11.03 | Performance fria/incremental/buscas/DB/RAM | implementado | 3 ensaios adicionais passaram gates; 1 ensaio anterior excedeu p95 lexical 1s e permanece registrado. |
| R11.04 | Branch/worktrees/falhas parciais/cancelamento | validado | Branches/worktrees, concorrência, rollback, SIGINT e retomada testados. |
| R12.01 | Executor benchmark A/B/C isolado/retomável | validado | A/B/C e confirmação A/E reais em workspaces isolados; A/E atual completou 72/72 com uso conhecido. |
| R12.02 | D Jev e E técnicas avançadas comparadas | bloqueado | D requer novas chamadas pagas e não foi executado; cinco chamadas reais anteriores validaram o conector. E teve três regressões antes da correção do redator. |
| R12.03 | 12 tarefas/3 famílias/3 repetições/arm | validado | Confirmação pós-correção A/E: 12 tarefas × 3 repetições × 2 braços = 72 execuções; ambos aceitaram 36/36. D fora da rodada. |
| R12.04 | Piloto separado/congelamento/holdout | validado | Piloto distinto; confirmação reservada de 12 tarefas; falhas pré-correção preservadas e versão corrigida confirmada separadamente. |
| R12.05 | Tokens reais/cache/output/reasoning sem dupla contagem | validado | Uso exec/app-server e hooks reais; cache como subconjunto de entrada e raciocínio como subconjunto de saída. |
| R12.06 | Todas tentativas/aceite/regressões/amortização | implementado | Uso disponível em todas as 72 tentativas atuais, falhas contabilizadas e indexação medida; releituras, compactações e quota não totalmente expostas. |
| R12.07 | Pareamento/incerteza/consumo assinatura | validado | Bootstrap pareado por tarefa na confirmação pós-correção: IC 95% 82,83%–85,30%; contador da assinatura indisponível. |
| R12.08 | Meta >=80% | validado | Pós-correção: 84,16% observado, IC 95% por tarefa 82,83%–85,30%, aceite 36/36 nos dois braços. Escopo de 12 tarefas pequenas, não garantia universal. |
| R13.01 | Rastreabilidade pesquisas | implementado | Matriz research.md e fontes acessíveis; rastreabilidade específica dos dois PDFs indisponível. |
| R13.02 | Documentação consistente/RC/evidências | implementado | Docs atualizados com métricas, 46 testes, build, lint, auditoria e instalação; escopo geral segue incompleto. |

Não atribuímos pendências de implementação a bloqueios externos. Os PDFs ausentes e a restrição de novos custos para o braço Jev são bloqueios concretos identificados; a credencial está disponível. As demais pendências são trabalho ainda necessário.
