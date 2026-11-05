# Checkpoint verificável — escopo integral incompleto

Atualizado em 2026-11-05. O produto 0.2.0 está instalado em `~/.local/bin/ce`, com estado em `~/.local/state/codex-economy` e perfil isolado em `~/.codex/economy.config.toml`. O código desta revisão está em `/home/leo-ribeiro/codex-economy-next`; a matriz `requirements.md` e o relatório `acceptance-report.md` detalham o escopo e os limites. O checkout inicial e evidências anteriores permanecem em `/home/leo-ribeiro/codex-economy`.

O índice, servidor MCP, adaptadores, execução, continuidade, recuperação e harnesses foram implementados e exercitados em fixtures. `evidence/tests-release-latest.txt`, `lint-release-corrected.txt`, `build-release-latest.txt` e `installed-source-match-latest.json` registram a verificação final. A primeira execução `tests-release-final.txt` falhou na coleta porque a virtualenv apontava para o checkout inicial; um caminho relativo permitiu coleta, mas falhou no subprocesso de trace; a correção é usar `PYTHONPATH` absoluto. O primeiro lint abrangente encontrou problemas de formatação nos scripts; estes foram corrigidos e a falha anterior mantida em `lint-release-final.txt`.

A confirmação A/E reservada mediu 84,04% de redução com 36/36 aceites por braço em 12 tarefas pequenas, agrupadas em quatro problemas repetidos em três linguagens. A/B/C anterior mediu 12,21% entre A e C, com consumo incompleto de uma tentativa B. A comparação D continua bloqueada pela instrução de não assumir novos custos: Jev já foi testado em cinco requisições reais, e `auxiliary.allow_paid` agora é falso por padrão. A qualidade equivalente e economia geral permanecem inconclusivas. As rodadas, incluindo falhas e tentativas interrompidas, não devem ser sobrescritas.

Faltam os dois PDFs especificados, uma confirmação independente da revisão endurecida em tarefas mais representativas, comparação D sob autorização de custos, teste real de delegação, demonstração de hooks descobertos por configuração local do projeto, teste em dispositivo Android e conservação binária integral de logs com UTF-8 inválido. Limites de assinatura e algumas contagens históricas não são expostos por interface suportada. `docs/research.md` rastreia recomendações disponíveis sem atribuir conteúdo aos PDFs ausentes.

Para continuar sem chamadas pagas:

```bash
cd /home/leo-ribeiro/codex-economy-next
PYTHONPATH=/home/leo-ribeiro/codex-economy-next/src /home/leo-ribeiro/codex-economy/.venv/bin/pytest -q
/home/leo-ribeiro/codex-economy/.venv/bin/ruff check src tests scripts
~/.local/bin/ce integrity
~/.local/bin/ce config
python3 scripts/metrics_preview.py
```

Preserve snapshots, hashes, manifests, logs e todas as tentativas ao preparar novo conjunto. Não execute `scripts/calibrate_jev_real.py` nem `scripts/validate_jev_ranking.py` enquanto chamadas faturáveis não estiverem autorizadas. Não contorne a política de custos nem inclua segredos em argumentos, logs ou repositórios.
