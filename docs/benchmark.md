# Benchmark e métricas coletadas

Este relatório separa a confirmação da meta, rodadas exploratórias, telemetria operacional, uso de Jev e desempenho local. Percentuais de intervenções sobre o mesmo conteúdo não são somados. Todo consumo Codex da comparação usa entrada + saída em todas as tentativas; tokens em cache são subconjunto da entrada e raciocínio é subconjunto da saída.

## Confirmação A/E atual

A confirmação pós-correção em `evidence/representative-confirmation-v3/` usou Codex CLI 0.167.0 com login ChatGPT, modelo `gpt-6.1-sol`, esforço `high`, timeout igual, configurações congeladas e workspaces separados. Comparou A (Codex de referência) e E (recuperação híbrida mais edição estruturada) em 12 tarefas sintéticas Python/Node/C++, com três repetições em cada braço: 72/72 tentativas tiveram uso conhecido.

| Braço | Aceitas | Tokens em todas as tentativas | Tokens por tarefa aceita |
|---|---:|---:|---:|
| A — referência | 36/36 | 3.068.801 | 85.244,47 |
| E — Lume | 36/36 | 486.053 | 13.501,47 |

A redução observada foi **84,1615%**. O bootstrap pareado agrupado por tarefa (12 grupos, preservando as três repetições) estimou intervalo de 95% de **82,8317% a 85,3003%**. Os 36 pares foram aceitos nos dois braços; não houve regressão de aceite. A regra pré-definida classificou a meta de 80% como **atingida nesta avaliação**. Isso é evidência para esse conjunto, não garantia geral.

O manifesto, resultados por tentativa, eventos, patches, verificações e ambiente estão em `evidence/representative-confirmation-v3/` e nos manifestos adjacentes. Os fixtures correspondentes estão em `tests/representative-inputs/`. Não execute novamente o manifesto congelado para substituir uma tentativa: use-o apenas para relatório. Toda confirmação futura requer manifesto e diretório de resultados novos.

## Rodadas anteriores preservadas

- `representative-confirmation-v2`: 72 tentativas completas, uso conhecido; A aceitou 36/36 e E 33/36. Redução observada de 82,05%, IC 95% 78,13%–83,95%. Veredito inconclusivo porque E falhou três vezes no caso Python de bearer. A causa foi corrigida e permanece registrada.
- `representative-confirmation-redaction-remediation`: repetição direcionada desse caso, 3/3 aceitas em ambos os braços e 84,38% observados. É seguimento de uma tarefa, não substitui a confirmação ampla.
- `representative-confirmation`: rodada interrompida após mudança do hash da configuração do Codex, com 24/72 tentativas. Continua separada e não participa do veredito atual.
- `representative-pilot`: piloto de três tarefas; seu tamanho não permite confirmar a meta geral.
- `benchmark`, `confirmation` e `confirmation-v2`: séries exploratórias/históricas A/B/C. Resultados incompletos, falhas e avisos metodológicos foram mantidos; não são a comparação A/E atual.
- Séries `editor-*`: medições de desenvolvimento anteriores à confirmação atual e às correções subsequentes. Não devem ser interpretadas como validação do código final.

Os detalhes por tentativa de todas as séries estão em `evidence/metrics-preview-tasks.csv`; os agregados, artefatos e alertas estão em `evidence/metrics-preview.json` e `.md`. O total histórico é **408 tentativas, 397 aceitas e 23.719.781 tokens observados** em experiências distintas. Há quatro tentativas históricas sem uso conhecido. Esse total não mede economia: mistura pilotos, avaliações parciais e confirmações, e não deve ser comparado como se fosse um único experimento.

## Outras métricas registradas

- Um snapshot histórico do CLI contém 78 execuções, 7 turnos Codex observados e 508.278 tokens (502.838 de entrada, dos quais 444.416 em cache; 5.440 de saída, dos quais 416 de raciocínio). Ele fica separado das séries experimentais para evitar possível dupla contagem. O CSV anonimizado por execução é `evidence/runtime-runs.csv`; a soma está em `evidence/runtime-metrics-summary.json`.
- Uma invocação Codex/MCP de validação, separada das experiências, registrou 64.577 tokens de entrada (43.136 em cache) e 196 de saída (14 de raciocínio), em `evidence/codex-profile-mcp-latest.jsonl`.
- Cinco chamadas reais Jev registraram 4.389 tokens de entrada e 751 de saída; latências e eventos estão nos artefatos Jev ligados por `metrics-preview.json`. O valor efetivamente cobrado e o contador da assinatura não estão disponíveis.
- Testes finais de desempenho usam carga sintética de três projetos e 600 arquivos. Os resultados respeitam os limites locais documentados pelo script; um ensaio anterior excedeu por pouco o limiar p95 lexical (1,043 s contra 1 s) e continua preservado. Isso não estabelece SLA para grandes repositórios.

## Regras de contagem e limitações

- Uso desconhecido não vira zero. Cache não é descontado dos tokens de entrada; ele é informado separadamente.
- Raciocínio informado é subconjunto da saída e não é somado de novo.
- Todas as tentativas, inclusive falhas, entram nos totais por braço. A aceitação é contada separadamente.
- Métrica local de bytes, ranking, duração ou custo de API não se converte em consumo do plano ChatGPT.
- A conta não fornece um contador suportado do limite de assinatura para o Codex CLI observado.
- A comparação D com chamadas Jev faturáveis permanece pendente; nenhuma inferência simulada foi rotulada como execução real.
- O executor não mede de forma completa releituras e compactações internas; Codex não expõe masking de histórico por estas interfaces.
- A confirmação usa tarefas pequenas e sintéticas. Não prova a mesma redução em todos os repositórios, famílias, modelos ou alterações.

## Reproduzir relatórios

Os relatórios são derivados dos dados versionados no próprio repositório; não dependem de outro checkout local:

```bash
python3 scripts/metrics_preview.py
ce benchmark evidence/representative-confirmation-v3-manifest.json --report
```

Não passe `--execute` ao manifesto histórico. Para uma nova avaliação, crie um manifesto novo, congele hashes de tarefas/configuração, preserve todas as tentativas e só então compare os braços.
