# Resultado de validação e limites

Estado: produto instalado e operável no Linux inspecionado, com critérios integrais ainda não satisfeitos. Não há certificação, auditoria independente nem aprovação humana. A matriz `requirements.md` traz o estado de cada requisito.

## Economia medida

Na confirmação reservada A/E, **12 tarefas pequenas** de Python, Node e C++, com três repetições e aceite definido previamente, foram aceitas **36/36** execuções por braço. A referência consumiu **3.014.722** tokens; a edição estruturada consumiu **481.275**. Isso representa **84,04% menos tokens por tarefa aceita** nesse ensaio. Entrada e saída são somadas; entrada em cache e raciocínio são subconjuntos, não somas adicionais.

O bootstrap agrupado por problema fornece intervalo de 95% de **83,09% a 84,94%**; há apenas quatro problemas algorítmicos subjacentes repetidos em três linguagens. Testes verificaram as tarefas e preservação de arquivos não alvo. A amostra não estabelece ganho ou qualidade equivalente em todos os projetos/tarefas industriais. A implementação foi endurecida depois da medição em controle de custos, remoção de extensões, estados de aceite e análise Gradle. Essas mudanças não alteraram o fluxo de edição medido; uma confirmação da versão endurecida ainda não foi executada.

O ensaio anterior A/B/C teve 108 tentativas. A e C aceitaram 36/36: **85.295,53** versus **74.880,39** tokens por aceita, redução de **12,21%**. Uma execução B falhou por limite da assinatura e não expôs consumo completo; seu custo por aceita é desconhecido. O piloto anterior de edição estruturada obteve 75,16% em apenas três tarefas. Tentativas interrompidas e falhas, incluindo a primeira variante que não acionou Codex por contexto insuficiente, foram preservadas.

Após mudanças posteriores, um novo piloto com três defeitos distintos em pequenos projetos de Python, Node e C++ aceitou 3/3 por braço; A consumiu 235.907 tokens e E 38.841. Uma confirmação separada com 12 defeitos distintos e 72 execuções foi iniciada; seu estado e dados estão em `evidence/representative-confirmation/`. Consulte o relatório gerado: um piloto ou fila ainda em execução não comprova a meta geral.

O objetivo de 80% foi **atingido no ensaio limitado A/E**, mas a validação integral permanece **inconclusiva**: D com Jev não foi comparado em confirmação completa, a falha de B tem consumo desconhecido e não há base para extrapolação ampla. A contagem do limite da assinatura não é disponibilizada pelo mecanismo suportado. Relatórios/raw: `evidence/editor-confirmation-r2/`, `evidence/confirmation-v2/`, `evidence/metrics-preview.json`. A pasta `codex-economy-next` contém os caminhos absolutos originais congelados da execução e deve ser mantida para reprodução literal; os inputs e fontes congeladas também foram preservados.

## Jev e custo

Jev real respondeu Choice, Score e Noul e ordenou evidências em uma fixture sintética explicitamente liberada. Calibração de Noul com 24 exemplos e holdout de 8/8 corretos cobre apenas definição de função, não correção geral. Cinco requisições reais estão contabilizadas em `evidence/jev-cost-record.json`.

A TypeSafe informa cobrança de **US$ 0,042 por milhão de tokens de entrada**, sem créditos gratuitos, conforme documentação consultada em 05/11/2026: https://help.typesafe.ai/articles/5187202169-how-much-does-jev-cost. O preço de tabela aplicado ao consumo registrado é uma estimativa; o valor efetivamente cobrado não está disponível. Não houve contratação de serviço ou recarga. Por restrição do usuário contra novos custos, novas chamadas pagas estão desligadas por padrão e o braço D permanece pendente. A confirmação de D exige autorização futura de custo; a chave já está guardada fora do Git e não precisa ser enviada novamente.

## Qualidade, instalação e segurança

A suíte final, lint, builds, auditorias de dependências e a correspondência entre fonte e instalação são registradas na pasta `evidence/`. A fixture Next passou em build e HTTP antes/depois; Android API 36 gerou APK e passou teste JVM antes/depois, com recurso alterado comprovado no APK; Gradle/Kotlin, CMake/CTest, Prisma/SQLite e Compose também tiveram percursos reais. Não houve teste em dispositivo Android ou cobertura semântica universal.

Os três ensaios mais recentes de performance passaram os limites previamente registrados para 600 arquivos pequenos. Um ensaio anterior excedeu o limite de busca p95: **1,043 s versus 1 s**; ele foi mantido em `evidence/performance-v2.json`. O maior RSS do modelo neural opcional foi aproximadamente 802 MiB. Resultados locais não são SLA universal.

MCP foi chamado realmente pelo Codex, inclusive na revisão instalada com `codex -p economy`: `evidence/codex-profile-mcp-latest.jsonl` registra chamada concluída de `evidence_search` e caminho retornado. Essa verificação separada consumiu 64.577 tokens de entrada, incluindo 43.136 em cache, e 196 de saída, incluindo 14 de raciocínio; não foi incluída no benchmark. A descoberta de hooks locais foi validada em projeto descartável com a opção oficial de confiança temporária aplicada a hooks previamente inspecionados (`evidence/hooks-project-latest.json`); em uso normal, a confiança depende do mecanismo oficial. O hook é diagnóstico, não intercepta requisições nem edita histórico. O app-server recebeu solicitação de interrupção após orçamento observado; o limite não é rígido para a requisição em andamento.

O banco migra de schema 1 para 3, registra backup antes de atualização e suporta recuperação offline que preserva banco anterior. O bundle inclui configuração e logs redigidos, mas não a credencial. Controle de acesso é local por usuário; subprocessos executam com permissões do usuário e não são sandbox de segurança geral. O armazenamento binário preserva bytes inválidos de UTF-8 depois da redação, para novas execuções; segredos substituídos e conteúdo além do limite de saída não são recuperáveis. Saídas de antes do schema 3 conservam somente o texto previamente registrado.

## Pendências concretas

- Comparação D com Jev real em confirmação: bloqueada pela restrição de novos custos; conector real já testado.
- Os dois PDFs nomeados pelo usuário não foram localizados; sua bibliografia específica não pôde ser rastreada.
- Relato completo de releituras/compactações históricas e contador da assinatura não são expostos por todas as interfaces; sem estimativas fabricadas.
- Teste Android em dispositivo e comprovação de confiabilidade em projetos grandes permanecem fora da evidência obtida.
- Delegação real foi validada em duas tarefas independentes com worktrees isoladas e verificações separadas (`evidence/delegation-live.json`), consumindo 192.975 tokens observados. Essa evidência limitada não garante qualidade de integração em tarefas gerais; delegação permanece desligada por padrão.
