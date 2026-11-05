# Uso da revisão 0.2

```bash
~/.local/bin/ce register projeto /raiz/autorizada
ce index projeto
ce capabilities projeto
ce search projeto 'erro exato' --mode lexical
ce context projeto 'investigar importação' --mode hybrid --budget 6000
ce read projeto src/main.py --start 1 --end 80 --hash HASH
ce graph projeto src/main.py --depth 2 --direction in --limit 30
ce refine projeto 'investigar importação' 'definição do contrato ausente'
ce entities projeto --kind build_target
ce map projeto
```

O orçamento de context mede o JSON UTF-8 completo, não tokens globais do Codex. Trechos nunca são abreviados. Pacotes pequenos podem omitir tudo e declarar insuficiência. O mapa e as relações informam origem e status; convenções de Next e schemas heurísticos são inferidos.

```bash
ce semantic projeto typescript
ce semantic projeto python
ce semantic projeto clang
ce build-model projeto cmake
ce build-model projeto gradle
ce run --timeout 120 --memory-mb 1024 --cpu-seconds 60 projeto -- python3 -m pytest
ce batch projeto @operacoes.json
ce trace projeto check.py
ce log RUN --stream stderr --start 1 --end 200
```

Opções de run devem preceder o nome do projeto por causa do separador de argv. Batch recebe `[{"id":"lint","argv":["npm","run","lint"]},{"id":"test","needs":["lint"],"argv":["npm","test"]}]`. Configuração de build é código confiável: somente execute em projetos autorizados. Gradle roda offline; falta de dependência em cache é erro explícito, sem fingir resolução. Modelos de build e semântica devem ser regenerados após atualização do índice que invalide seus fatos.

```bash
ce config
ce config --set '{"context_bytes":6000,"profiles":{"lean":{"model":null,"effort":"low"}}}'
ce task projeto 'objetivo' 'aceite' --model-profile lean --verify '["python3","check.py"]'
ce task projeto 'objetivo' 'aceite' --harness app-server --observed-token-budget 100000
ce task projeto 'objetivo' 'aceite' --harness patch --verify '["npm","test"]'
ce session projeto 'objetivo' 'aceite'
ce handoff SESSION
ce continuity SESSION --budget 4000
ce accept SESSION RUN_VERIFICADO
```

O harness patch usa instruções próprias para produzir JSON, sem conceder permissão de escrita ao modelo. A aplicação aplica substituições originais únicas e verifica hashes. Contexto insuficiente dispara até duas localizações dirigidas sob o mesmo timeout. Um patch aplicado permanece sem aceite até verificação independente. Um run antigo, de outro projeto, que falhou ou cuja fonte mudou é rejeitado pelo aceite.

App-server interrompe após consumo informado, portanto uma requisição em curso pode ultrapassar o orçamento. Preserve thread/session e use `--thread THREAD` para retomada, ou carregue handoff. O CLI comum não pode interceptar todas as leituras ou alterar observações internas.

```bash
ce integrate
codex -p economy
ce setup projeto
ce setup projeto --hooks
ce setup projeto --remove
ce integrate --remove
```

O perfil separado não reescreve config.toml. A skill fica em `.agents/skills/codex-economy/SKILL.md`; hooks opcionais ficam em `.codex/hooks.json`. Arquivos alheios ou editados externamente não são sobrescritos. Hooks exigem revisão/confiança pelo mecanismo oficial do Codex e são diagnósticos, sem bloqueio ou edição de contexto. Não configure um hook para chamar uma ferramenta de edição automaticamente.

```bash
ce policy projeto
ce policy projeto --set '{"external":false}'
ce secret                     # somente presença, nunca o valor
ce secret --stdin             # recebe a chave TypeSafe via stdin, sem argumento de comando
ce secret --remove
ce config --set '{"auxiliary":{"mode":"off"}}'
# Inferência Jev faturável só funciona se explicitamente habilitada na configuração:
ce config --set '{"auxiliary":{"mode":"auto","allow_paid":true}}'
ce calibrate dados-calibracao.json
ce experiment projeto 'consulta' --budget 6000
ce neural projeto docs/architecture.md --rate 0.5
```

Cada registro de calibração tem `split:"calibration"`, `probability` numérica e `label` 0/1; conjuntos finais são rejeitados. Limiares não são garantia. Jev real exige chave, permissão explícita para chamadas faturáveis e política externa do projeto; as variantes locais continuam funcionando. A desativação impede inferência auxiliar, sem alterar a autenticação do Codex. O modelo neural opcional reside em `~/.local/share/codex-economy/experimental`, usa cerca de 0,8 GiB RSS no ensaio registrado e não utiliza rede na execução.

```bash
ce backup /local/novo.sqlite
ce backup /local/novo.tgz --bundle
ce restore /local/novo.tgz
ce recover --source /local/backup.sqlite
ce recover                    # reinicia estado, preservando banco anterior em arquivo de recuperação
ce integrity
ce prune --days 30
ce export /local/novo.json
ce metrics
```

Pare outros processos ce/MCP antes da recuperação offline. Reset preserva projetos no disco, mas requer recadastro se não houver backup de registro. Bundle restaura banco e configuração; credenciais continuam no cofre original e não são incluídas. Backups/exports contêm fonte e logs: armazenagem privada 0600; não publique sem revisão. A retenção limita cache de extração e remove eventos/runs expirados e snapshots não referenciados.

Instale/atualize com `scripts/install.sh`; releases ficam isoladas e o runtime aponta para a atual. `scripts/rollback.sh` troca o binário anterior; restaure também o backup pré-upgrade quando houver downgrade de schema. `scripts/uninstall.sh` remove runtime/releases próprias e preserva estado, credenciais, projetos e modelos/toolchains opcionais.
