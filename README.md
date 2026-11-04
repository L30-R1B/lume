# codex-economy 0.1.0

Ferramenta local de seleção de evidências e execução mensurada de tarefas Codex. **O escopo integral solicitado ainda não está concluído nem validado para produção.** Veja `docs/requirements.md` e `docs/checkpoint.md`. A meta de 80% não está demonstrada.

Requer Linux, Python 3.12+, Git; Node para análise TypeScript, CMake/GCC para os exemplos C++. O runtime fica isolado em `~/.local/share/codex-economy/runtime`; o estado em `~/.local/state/codex-economy` (`CE_HOME` permite outro diretório).

```bash
./scripts/install.sh
~/.local/bin/ce register meu-projeto /caminho/absoluto
~/.local/bin/ce index meu-projeto
~/.local/bin/ce search meu-projeto 'mensagem exata' --mode lexical
~/.local/bin/ce context meu-projeto 'validar pedido' --budget 6000
~/.local/bin/ce read meu-projeto src/main.py --start 1 --end 80 --hash HASH
~/.local/bin/ce graph meu-projeto src/main.py --depth 2 --limit 20
~/.local/bin/ce run meu-projeto -- python3 -m pytest
~/.local/bin/ce integrate
codex -p economy
```

Saídas são JSON; `ce --human ...` aplica indentação. `ce --help` lista todas as operações. `run` recebe argumentos após `--`; não interpreta shell. Subprocessos executam com as permissões do usuário: não é sandbox de comandos arbitrários. MCP expõe somente seis operações de evidência sobre projetos cadastrados; não oferece execução de comandos.

`ce task PROJETO 'objetivo' 'aceite'` prepara índice/contexto, executa o Codex instalado com sua autenticação e registra sessão, eventos e consumo. Não declara aceite automaticamente: verifique o patch e rode os critérios de aceite. `ce session`, `ce handoff ID --patch '{"next_step":"..."}'` preservam continuidade.

`ce integrate` instala o perfil `economy.config.toml`, sem alterar a configuração principal. `ce integrate --remove` remove esse perfil. O perfil pré-autoriza as operações do MCP local dentro dos projetos cadastrados. Use somente raízes autorizadas. Uma sessão anterior precisa ser reiniciada com `codex -p economy`. A skill curta em `docs/economy-SKILL.md` é fornecida para instalação explícita; ainda não é instalada automaticamente.

```bash
npm install --prefix ~/.local/share/codex-economy/node typescript@5.9.3
ce semantic meu-projeto typescript
# C/C++: gere build/compile_commands.json antes
ce semantic meu-projeto clang
ce doctor
ce integrity
ce backup /caminho/novo-backup.sqlite
ce restore /caminho/backup.sqlite
ce log IDENTIFICADOR --stream stderr --start 1 --end 200
ce prune --days 30
```

Atualize rodando `scripts/install.sh` novamente. Desinstale com `scripts/uninstall.sh`: projetos, credenciais, backups e estado são preservados. Não altere `CE_PREFIX` para diretórios de terceiros.

Detalhes de arquitetura, privacidade, manutenção, limitações, benchmark e fontes: `docs/operations.md`, `docs/research.md`, `docs/requirements.md`.
