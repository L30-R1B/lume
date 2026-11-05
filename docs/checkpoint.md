# Checkpoint verificável — escopo integral incompleto

Atualizado em 2026-11-05. Código em `/home/leo-ribeiro/codex-economy-next`, instalação em `~/.local/bin/ce`, perfil `~/.codex/economy.config.toml`, estado `~/.local/state/codex-economy`. Banco migrado a schema 3 com backup prévio. `docs/requirements.md` registra requisitos e `docs/acceptance-report.md` resultados e limites. A revisão atual foi instalada; os 30 arquivos do pacote coincidem com a fonte segundo `evidence/installed-source-match-schema3.json`.

A recuperação de saídas novas por faixas de bytes após redação, migração v2→v3 e backup foram implementadas. Execuções antigas conservam apenas o texto anterior e segredos redigidos ou conteúdo além do limite não são recuperáveis. A suíte completa após as alterações passou com 44 testes (`evidence/tests-schema3-benchmark-final.txt`); a recuperação binária pelo transporte MCP real passou em `evidence/tests-mcp-bytes.txt`.

Dois trabalhadores Codex reais realizaram tarefas independentes e passaram verificações em worktrees isoladas (`evidence/delegation-live.json`); os 192.975 tokens observados não pertencem aos benchmarks. Hooks de projeto foram descobertos em fixture descartável com a opção oficial de confiança temporária para a definição inspecionada (`evidence/hooks-project-latest.json`). Seu setup cria a camada de configuração necessária quando ausente e preserva config preexistente.

O piloto A/E com três defeitos distintos foi aceito 3/3 por braço (235.907 e 38.841 tokens). A confirmação separada de 12 defeitos × 3 repetições × 2 braços começou em `evidence/representative-confirmation/`; verifique `results.jsonl`, `representative-confirmation-worker.log`, stderr e estado do processo antes de fazer qualquer intervenção. **Não altere arquivos `src/codex_economy` nem fixtures congeladas enquanto o worker estiver ativo**: seus hashes estão no manifest. A fila tem lock, registra tentativas antes de continuar e pode parar diante de alteração de configuração, quota ou resposta sem métricas. Não sobrescreva workspaces nem apague falhas. O consumo não autoriza inferir a meta enquanto a fila estiver em andamento.

Um emulador Android headless foi instalado em prefixo próprio e iniciado por emulação de software; não há dispositivo físico conectado nem permissão KVM para este usuário. Ele ainda não completou o boot no último registro. Diagnósticos em `evidence/android-emulator-*`. Pare apenas o processo próprio do emulador depois do ensaio; não altere grupos/permissões do sistema ou serviços alheios.

Continuam bloqueados o braço D por instrução de não assumir novos custos e a rastreabilidade específica dos dois PDFs não encontrados. A chave Jev existe e chamadas pagas permanecem desabilitadas; não execute scripts Jev reais sem autorização de custos. Outros limites e pendências de qualidade permanecem detalhados no relatório; não atribua ao produto aprovação total.

Comandos úteis sem serviços pagos:

```bash
cd /home/leo-ribeiro/codex-economy-next
wc -l evidence/representative-confirmation/results.jsonl
tail -n 10 evidence/representative-confirmation-worker.log
tail -n 20 evidence/representative-confirmation-worker.stderr
PYTHONPATH=/home/leo-ribeiro/codex-economy-next/src /home/leo-ribeiro/codex-economy/.venv/bin/pytest -q
/home/leo-ribeiro/codex-economy/.venv/bin/ruff check src tests scripts
~/.local/bin/ce integrity
~/.local/bin/ce config
python3 scripts/metrics_preview.py
```

Após a fila terminar, gere relatório com o mesmo manifest, confira aceite, todas as tentativas, consumo e intervalos, capture evidências, teste instalação/atualização/rollback e atualize a documentação sem inventar resultados. Se a fila interromper, reconcilie a tentativa usando o mecanismo do executor antes de retomar; limites de assinatura não autorizam descartá-la.
