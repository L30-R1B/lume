# codex-economy 0.2.0

Aplicação local para recuperar evidências, controlar saídas e executar tarefas Codex com consumo rastreável, preservando o login ChatGPT. **A meta de 80% depende dos resultados do experimento; não é uma propriedade presumida do produto.** O estado de validação e os bloqueios externos estão em [docs/acceptance-report.md](docs/acceptance-report.md).

```bash
./scripts/install.sh
~/.local/bin/ce register projeto /raiz/do/projeto
~/.local/bin/ce index projeto
~/.local/bin/ce context projeto 'problema a investigar' --budget 6000
~/.local/bin/ce integrate
codex -p economy
```

Para execução completa com verificação independente:

```bash
ce task projeto 'objetivo' 'critério de aceite' --verify '["npm","test"]'
ce task projeto 'objetivo' 'critério de aceite' --harness patch --verify '["python3","check.py"]'
ce task projeto 'objetivo' 'critério de aceite' --harness app-server --observed-token-budget 100000
```

O harness `patch` é um fluxo separado de edições estruturadas: o modelo opera em sandbox de leitura e devolve substituições originais exatas; o software verifica hashes, aplica e testa. O MCP não intercepta automaticamente ferramentas nativas nem modifica o histórico do Codex. Orçamento de contexto é o JSON completo em bytes; orçamento de tarefa no app-server interrompe após consumo observado, sem prometer teto rígido por requisição.

Linux/Python 3.12+; Node/TypeScript, Java/Gradle/Kotlin, CMake/libclang e demais ferramentas são necessários conforme o adaptador. Instalação usa releases isoladas em `~/.local/share/codex-economy`; estado em `~/.local/state/codex-economy`; `CE_HOME`, `CE_PREFIX` e `CE_BIN` permitem instalações separadas. Configuração, credenciais e projetos alheios são preservados.

- [Comandos, configuração e operação](docs/usage-v2.md)
- [Arquitetura e notas da revisão](docs/release-0.2.md)
- [Validação e limitações](docs/acceptance-report.md)
- [Requisitos e rastreabilidade](docs/requirements.md)
- [Pesquisa e fontes](docs/research.md)
- [Metodologia de benchmark](docs/benchmark.md)

Atualize executando `scripts/install.sh` novamente. Use `scripts/rollback.sh` para trocar o runtime anterior e backup compatível para downgrade de schema. `scripts/uninstall.sh` preserva projetos, credenciais, estado e toolchains/modelos opcionais. `ce --help` apresenta o catálogo completo; saída padrão é JSON e `ce --human ...` aplica indentação.
