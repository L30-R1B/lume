# Checkpoint verificável — escopo incompleto

Esta é continuidade de implementação, não entrega substituta de produto completo. A matriz requirements.md identifica todas as lacunas conhecidas. Não há aprovação de produção nem meta de 80% demonstrada.

Código: /home/leo-ribeiro/codex-economy. Instalado: ~/.local/bin/ce → ~/.local/share/codex-economy/runtime/bin/ce. Estado: ~/.local/state/codex-economy/state.sqlite. Perfil: ~/.codex/economy.config.toml, base config preservada por hash. Credenciais do Codex não foram extraídas. Jev não recebeu chamada real por ausência de chave disponibilizada no ambiente.

Validado até este checkpoint: 14 testes comportamentais sem skips, build wheel/sdist, lint, auditoria de dependências sem vulnerabilidades conhecidas após upgrade do pip, instalação/update/remoção isoladas, integridade, performance local 600 arquivos/3 projetos, MCP stdio pelo SDK e chamado realmente pelo Codex, referências reais TS/Clang, compilação Kotlin JVM e fluxo fim a fim com patch aceito independentemente. Evidências em evidence/tests.txt, lint.txt, build.txt, dependency-audit.json, installation-cycle.json, profile-lifecycle.json, performance.json, codex-mcp-approved.jsonl e e2e-report.json.

Benchmark exploratório interrompido com dados preservados: 31 jobs finalizados mais tentativa cancelada; aviso de contaminação por formatação nas fixtures. Não usar como confirmação nem ignorar cancelamento. A confirmação usa 12 tarefas reservadas x 3 braços x 3 repetições (108 jobs), entradas/implementação hashadas, C++/Python/Node e verificação independente de escopo/testes. É um conjunto de funções pequenas, insuficiente para extrapolar à manutenção industrial ampla.

A confirmação está em serviço systemd de usuário de execução única `codex-economy-confirmation`. Sem recorrência/agendamento. Pode concluir depois deste arquivo. Consulte o estado real, não esta descrição:

```bash
systemctl --user status codex-economy-confirmation
journalctl --user -u codex-economy-confirmation -n 20 --no-pager
cat evidence/confirmation-worker-status.json
ce benchmark /home/leo-ribeiro/codex-economy/evidence/confirmation-manifest.json --report
```

Não execute outro worker enquanto o serviço estiver ativo. `--execute` retoma os jobs já registrados, mas workspace interrompido não é sobrescrito: reconcilie com runs/artefatos e preserve tentativa antes de recomeçar. Não mude os arquivos de src/ nem inputs durante confirmação: hashes da implementação congelados estão no manifest. Configuração principal do Codex também foi registrada por hash; mudanças durante o experimento invalidam condições equivalentes.

Próximas ações necessárias: concluir/analisar confirmação A/B/C; testar equivalência de qualidade e meta; continuar os requisitos pendentes na matriz, particularmente Android/Gradle completo, relações Next, contratos e alvos de build, recuperação de corrupção/migrações, cache auxiliar/tarefa, política automática de continuidade, expansão progressiva e estratégias experimentais. Rodadas D e calibração real dependem de Jev disponibilizado pelo mecanismo de segredo apropriado. PDFs ausentes impedem somente rastreabilidade específica de seu conteúdo, não justificam as demais pendências.

Para continuar a validação local:

```bash
cd /home/leo-ribeiro/codex-economy
.venv/bin/pytest -q
.venv/bin/ruff check --config pyproject.toml src tests
.venv/bin/python -m build
.venv/bin/pip-audit
ce integrity
```

Após a confirmação terminar e antes de alterar a implementação, preserve report/raw/manifests. Novas configurações e otimizações usam novos diretórios de resultado, sem apagar tentativas anteriores. O campo complete do relatório significa apenas fila concluída. A meta e a conclusão de todo o escopo exigem avaliação separada e honesta.
