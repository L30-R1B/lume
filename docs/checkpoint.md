# Checkpoint de validação

Atualizado em 2026-11-09. O produto Lume / `codex-economy` 0.2.0 foi instalado e operado no ambiente Linux de validação; o banco local usa schema 3. A atualização e o smoke test fora do checkout passaram. O relatório final da matriz está em `docs/requirements.md`; o escopo global continua incompleto pelas pendências abaixo.

## Economia medida

A confirmação vigente usa o release instalado, Codex CLI 0.167.0 autenticado no plano ChatGPT, modelo `gpt-6.1-sol`, esforço `high`, configuração copiada para um `CODEX_HOME` isolado e autenticação reutilizada por symlink. Manifest, hashes e versão estão em `evidence/representative-confirmation-v3-manifest.json` e `evidence/representative-confirmation-v3/environment.json`.

Foram concluídas **72/72 execuções** em 12 tarefas distintas de Python, Node e C++, três repetições por braço. A e E aceitaram 36/36 tarefas pareadas. A consumiu 3.068.801 tokens (85.244,47 por aceita); E consumiu 486.053 (13.501,47 por aceita). Redução observada **84,16%**, bootstrap de 95% agrupado pelos 12 problemas **82,83%–85,30%**; a meta está atingida nesta avaliação. Isso não garante a mesma redução para projetos ou classes de tarefa diferentes.

A confirmação `v2` anterior teve três regressões em E causadas por uma regra de redação que alterava o literal de código `"Bearer "` dentro de JSON. A regra foi corrigida, coberta por teste e o caso passou 3/3 em A e E no acompanhamento direcionado. As 72 execuções pós-correção estão separadas em `evidence/representative-confirmation-v3/`; o resultado anterior foi preservado em `evidence/representative-confirmation-v2/`. Uma rodada antiga 24/72 interrompida após mudança de configuração permanece em `evidence/representative-confirmation/` e não foi combinada.

A prévia de todas as experiências está em `evidence/metrics-preview.json`, com tabela em `evidence/metrics-preview.md` e detalhamento por tarefa em `evidence/metrics-preview-tasks.csv`. Ela inclui 408 tentativas históricas, não representa uma única comparação. No ensaio atual, cache é subconjunto da entrada e raciocínio é subconjunto da saída; nenhum foi somado duas vezes. Quatro tentativas antigas não expõem uso. O contador de consumo da assinatura não está disponível.

## Validação do produto

- 46 testes comportamentais passaram; ruff, build e auditoria de 47 dependências runtime passaram. `evidence/dependency-audit-final.json` registra zero vulnerabilidades conhecidas.
- A instalação local atual foi atualizada. Os 30 arquivos Python/CJS instalados coincidem com a fonte em `evidence/installed-source-match-after-redaction.json`.
- Instalação limpa, upgrade, rollback, remoção e preservação passaram em 10 operações isoladas: `evidence/release-schema3-latest.json`.
- MCP real pelo Codex, hooks diagnósticos, app-server e delegações reais têm evidências separadas. A chamada Codex/MCP consumiu 64.577 tokens de entrada; duas delegações consumiram 192.975. Esses usos não fazem parte do benchmark A/E.
- Cinco pedidos Jev reais históricos estão medidos na prévia; nenhum pedido pago foi feito nesta continuação.
- Android API 36 compilou APK e passou testes JVM. A tentativa adicional de emulador iniciou após 1.298.868 ms, mas `system_server` abortou; não há aparelho conectado e o usuário não tem permissão KVM. O APK não foi instalado. Evidência: `evidence/android-emulator-runtime.json`.

## Pendências concretas

- O braço D com Jev requer novas chamadas pagas; permanece bloqueado pela restrição de custos. A integração real foi exercitada anteriormente, mas não foi comparada como braço de benchmark.
- Os dois PDFs nomeados pelo usuário não estavam disponíveis; a rastreabilidade de suas recomendações e bibliografias específicas continua bloqueada.
- Teste Android em dispositivo/emulador funcional e avaliação em repositórios grandes não foram demonstrados. A performance local cobre a carga sintética declarada nos relatórios, sem constituir SLA universal.
- O CLI não expõe de forma suportada o consumo do limite de assinatura nem todos os rereads/compactações/histórico interno. Não foram estimados.
- A CLI normal não é interceptada pelo MCP; limites de intervenção, cancelamento e hooks são os declarados no produto.

Não alegar certificação, auditoria independente, aprovação humana ou conclusão total. A meta de 80% foi atingida apenas para a avaliação A/E pós-correção registrada acima.

## Comandos reproduzíveis

```bash
python3 -m pytest -q
ruff check --config pyproject.toml src tests scripts
ce integrity
ce doctor
ce benchmark evidence/representative-confirmation-v3-manifest.json --report
python3 scripts/metrics_preview.py
```

Instalação/atualização: `bash scripts/install.sh`; skills: `bash scripts/install_skills.sh`. Para trabalhar em outro projeto, registre a raiz e execute `ce setup` antes de `ce index`; depois use as ferramentas `search`, `read`, `graph`, `impact`, `context` ou o MCP configurado.
