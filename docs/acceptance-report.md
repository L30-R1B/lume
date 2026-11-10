# Resultado de validação e limites

Estado: produto instalado e operável no Linux inspecionado, com critérios integrais ainda não satisfeitos. Não há certificação, auditoria independente nem aprovação humana. A matriz `requirements.md` traz o estado de cada requisito.

## Economia medida

Na confirmação pós-correção, A/E executaram **12 tarefas distintas** em Python, Node e C++, com três repetições por braço: 72/72 tentativas registradas, todas com consumo conhecido e todas aceitas. A somou **3.068.801 tokens** (**85.244,47 por tarefa aceita**) e E **486.053** (**13.501,47 por aceita**), redução observada de **84,16%**. O bootstrap pareado por tarefa (12 grupos, três repetições) deu intervalo de 95% de **82,83% a 85,30%**. A meta de 80% está **atingida nesta avaliação representativa**: os 36 pares passaram e o intervalo inteiro fica acima de 80%.

Antes dessa correção, a rodada `representative-confirmation-v2` aceitou 36/36 em A e 33/36 em E: a redução observada foi 82,05%, com intervalo de 78,13%–83,95%, e o veredito ficou inconclusivo. A causa foi o redator de logs transformar o literal de código `"Bearer "` em `[REDACTED]` dentro da resposta JSON. Corrigi a regra e acrescentei um teste comportamental que mantém o literal intacto e redige uma credencial real. O acompanhamento direcionado passou 3/3 em cada braço, com 84,38% observado. A confirmação completa pós-correção está em `representative-confirmation-v3`; nenhum dado da versão anterior foi apagado ou substituído.

O piloto distinto, com três tarefas, aceitou 3/3 em A e E e observou 83,54%; seu relatório mantém a meta geral como inconclusiva por ser somente piloto. Uma confirmação mais antiga, executada em código diferente e com quatro problemas subjacentes, mediu 84,04%; ela não substitui a confirmação atual. O experimento exploratório A/B/C teve 108 tentativas, com redução de 12,21%; uma execução B não expôs consumo. Todos esses dados e falhas permanecem separados e preservados.

Um experimento anterior de 24/72 tentativas foi interrompido quando mudou o hash da configuração do Codex; foi mantido em `evidence/representative-confirmation/`, sem combinar seus resultados com as confirmações atuais. Os resultados A/E pré e pós-correção, o acompanhamento e os dados por tarefa estão em `evidence/representative-confirmation-v2/`, `evidence/representative-confirmation-redaction-remediation/`, `evidence/representative-confirmation-v3/` e `evidence/metrics-preview.json`. O contador de uso da assinatura não está disponível por interface suportada.

## Jev e custo

Jev real respondeu Choice, Score e Noul e ordenou evidências em uma fixture sintética explicitamente liberada. Calibração de Noul com 24 exemplos e holdout de 8/8 corretos cobre apenas definição de função, não correção geral. Cinco requisições reais estão contabilizadas em `evidence/jev-cost-record.json`.

A TypeSafe informa cobrança de **US$ 0,042 por milhão de tokens de entrada**, sem créditos gratuitos, conforme documentação consultada em 05/11/2026: https://help.typesafe.ai/articles/5187202169-how-much-does-jev-cost. O preço de tabela aplicado ao consumo registrado é uma estimativa; o valor efetivamente cobrado não está disponível. Não houve contratação de serviço ou recarga. Por restrição do usuário contra novos custos, novas chamadas pagas estão desligadas por padrão e o braço D permanece pendente. A confirmação de D exige autorização futura de custo; a chave já está guardada fora do Git e não precisa ser enviada novamente.

## Qualidade, instalação e segurança

A suíte atual passou com **46 testes**, lint e build; a auditoria encontrou zero vulnerabilidades conhecidas nas 47 dependências runtime. A atualização local concluiu, os 30 arquivos Python/CJS instalados coincidem com a fonte, e a validação isolada de instalação/atualização/rollback/desinstalação passou 10 operações preservando estado e projeto. Evidências: `tests-final-v3.txt`, `dependency-audit-final.json`, `installed-source-match-after-redaction.json` e `release-schema3-latest.json`. A fixture Next passou em build e HTTP antes/depois; Android API 36 gerou APK e passou teste JVM antes/depois, com recurso alterado comprovado no APK; Gradle/Kotlin, CMake/CTest, Prisma/SQLite e Compose também tiveram percursos reais. Não houve teste bem-sucedido em dispositivo Android ou cobertura semântica universal.

Os três ensaios mais recentes de performance passaram os limites previamente registrados para 600 arquivos pequenos. Um ensaio anterior excedeu o limite de busca p95: **1,043 s versus 1 s**; ele foi mantido em `evidence/performance-v2.json`. O maior RSS do modelo neural opcional foi aproximadamente 802 MiB. Resultados locais não são SLA universal.

MCP foi chamado realmente pelo Codex, inclusive na revisão instalada com `codex -p economy`: `evidence/codex-profile-mcp-latest.jsonl` registra chamada concluída de `evidence_search` e caminho retornado. Essa verificação separada consumiu 64.577 tokens de entrada, incluindo 43.136 em cache, e 196 de saída, incluindo 14 de raciocínio; não foi incluída no benchmark. A descoberta de hooks locais foi validada em projeto descartável com a opção oficial de confiança temporária aplicada a hooks previamente inspecionados (`evidence/hooks-project-latest.json`); em uso normal, a confiança depende do mecanismo oficial. O hook é diagnóstico, não intercepta requisições nem edita histórico. O app-server recebeu solicitação de interrupção após orçamento observado; o limite não é rígido para a requisição em andamento.

O banco migra de schema 1 para 3, registra backup antes de atualização e suporta recuperação offline que preserva banco anterior. O bundle inclui configuração e logs redigidos, mas não a credencial. Controle de acesso é local por usuário; subprocessos executam com permissões do usuário e não são sandbox de segurança geral. O armazenamento binário preserva bytes inválidos de UTF-8 depois da redação, para novas execuções; segredos substituídos e conteúdo além do limite de saída não são recuperáveis. Saídas de antes do schema 3 conservam somente o texto previamente registrado.

## Pendências concretas

- Comparação D com Jev real em confirmação: bloqueada pela restrição de novos custos; conector real já testado.
- Os dois PDFs nomeados pelo usuário não foram localizados; sua bibliografia específica não pôde ser rastreada.
- Relato completo de releituras/compactações históricas e contador da assinatura não são expostos por todas as interfaces; sem estimativas fabricadas.
- Teste Android em dispositivo e comprovação de confiabilidade em projetos grandes permanecem fora da evidência obtida.
- Delegação real foi validada em duas tarefas independentes com worktrees isoladas e verificações separadas (`evidence/delegation-live.json`), consumindo 192.975 tokens observados. Essa evidência limitada não garante qualidade de integração em tarefas gerais; delegação permanece desligada por padrão.
