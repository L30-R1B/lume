# Lume / ce capability catalog

This catalog describes the installed Codex Economy CLI and its MCP server. Use ce --help and ce COMMAND --help to confirm exact options for the installed release. Default CLI output is compact JSON; put global options before the command (for example: ce --human status NAME). Executable: ~/.local/bin/ce when it is not on PATH.

## Project records, indexing, and policy

- register NAME ROOT, projects: register an absolute project root and list registered roots. Names accept letters, digits, dot, underscore, hyphen. Registration does not authorize parent/sibling projects.
- index NAME [--force]: incrementally index the current source snapshot, including uncommitted files. Rebuilds derived graph facts and invalidates on root, Git HEAD, policy, source, and extractor changes. Force re-extracts; use only for an intentional rebuild.
- status NAME: missing, stale, partial, or ready; includes snapshot/fingerprint and omissions.
- capabilities NAME: report per-project adapter/build/test/evidence coverage.
- commands NAME: detected build/test commands. Inspect before executing project scripts.
- map NAME: hierarchical project inventory and evidence pointers.
- policy NAME [--set JSON]: read or update exclusions, external-send permission, and max file size. External send is false by default.
- doctor, integrity: Codex/auth capability checks and SQLite/foreign-key health; never expose auth secrets.
- semantic NAME {typescript,python,clang}: invoke the project's available semantic adapter.
- build-model NAME {gradle,cmake}: analyze supported build metadata using the declared build system.
- entities NAME [--kind KIND] [--limit N]: query indexed contracts such as tests, build targets, schemas, services, resources, and documents.

Adapter coverage depends on installed tools and project configuration. Parsing and inferred graph edges are not complete semantic resolution. A partial index must be described as partial; unknown technologies still support faithful inventory, search, and source reads.

## Search, evidence, graph, and context

- search NAME QUERY: shortlist original evidence using one of:
  - lexical: exact terms/messages and BM25; use for identifiers and errors.
  - structural: indexed symbol names/spans; use for definitions.
  - hybrid: lexical plus local character n-gram reranking; good default, no network.
  - full: whole candidate files under the configured byte budget/line limits.
  - assisted: local ranking plus Jev only when auxiliary mode, key, and project external policy permit it; may make a paid external request.
  - hierarchical: hybrid ranking with bounded graph/topic-document expansion.
  - ast-prune: exact symbol spans and structural candidates; not token deletion or paper-equivalent SWE-Pruner.
  - longcodezip: bounded coarse-to-fine selection; not a claim of reproducing trained LongCodeZip.
- context NAME QUERY [--mode MODE --budget BYTES --limit N]: package original source spans, paths, lines, hashes, relations, tests, and omissions. Budget is serialized UTF-8 evidence bytes, not total JSON envelope or a Codex token cap. Empty/insufficient context is explicit; refine with a missing fact rather than assuming.
- read NAME PATH [--start N --end N --hash SHA256]: read current, confined source exactly. Hash preconditions reject stale selected evidence.
- graph NAME PATH [--depth 1..4 --direction {in,out,both} --kind KIND --limit N]: bounded file relations with origin/status.
- impact NAME PATH: bounded incoming-impact view.
- refine NAME QUERY MISSING_FACT [--budget BYTES]: targeted follow-up, reports whether it found new evidence.
- experiment NAME QUERY [--budget BYTES]: compare faithful/local selection variants and report retrieval bytes/time. This is not a Codex task token-saving estimate.
- neural NAME PATH [--rate R]: optional local LLMLingua document experiment if its separately installed model exists. It only analyzes eligible documentation excerpts; source returned for editing remains original. Not a Codex task savings metric.
- trace NAME SCRIPT [ARGS...]: collect supported dynamic execution evidence for one script; scope is that trace only.

## Command execution, tasks, and continuity

- run NAME -- ARGV...: execute a command without shell concatenation; saves exit code, redacted stdout/stderr, duration and truncation state. Optional timeout/output/resource limits are shown by ce run --help. Project build commands may execute repository code: use only in the user-authorized project.
- batch NAME JSON_OR_@FILE: run a declared set of operations with dependency ordering; each operation retains its own result.
- log RUN_ID [--stream stdout|stderr --start LINE --end LINE]: retrieve persisted output ranges; --bytes --offset N --length N gives a bounded base64 range of redacted output.
- session NAME OBJECTIVE ACCEPTANCE: persist task objective and criteria.
- handoff SESSION [--patch JSON --state active|blocked|accepted|failed]: read/update short session state.
- continuity SESSION [--budget BYTES]: select continue/refresh/handoff based on snapshot validity and state size.
- accept SESSION RUN_ID...: mark accepted only when all verification runs completed successfully for the same project and current fingerprint.
- task NAME OBJECTIVE ACCEPTANCE: launch a separate Codex CLI execution, log its usage when exposed, and optionally run a JSON argv acceptance command via --verify '["pytest","-q"]'. Harnesses: exec (default), app-server (thread and observed-usage interruption), and patch (structured source replacements with hash validation). This launches another model process; an active Codex agent should usually work directly instead of recursively calling it.
- delegate NAME JSON_FILE: explicitly run configured independent sub-tasks. Delegation is opt-in and can increase total usage.

Do not claim a task accepted unless independent checks succeeded. Failed runs remain evidence and are not deleted to improve a metric.

## MCP, Codex integration, and project extensions

- integrate creates/refreshes the separate Codex profile economy.config.toml; start Codex with codex -p economy. integrate --remove removes only that managed profile. Base config.toml is preserved.
- setup NAME adds the project skill .agents/skills/codex-economy/SKILL.md. setup NAME --remove removes only unchanged managed content. --hooks adds optional diagnostic-only hooks; they do not block calls or rewrite context.
- mcp starts the local stdio server. It has no network listener and is normally started by Codex.
- MCP tool catalog:
  - evidence_search(project, query, mode="hybrid", budget=6000): bounded evidence context.
  - evidence_read(project, path, start=1, end=200, expected_hash=None): exact source read with optional hash check.
  - evidence_graph(project, path, direction="both", kind=None, depth=1, limit=30): bounded relations with provenance.
  - evidence_refresh(project): update a registered project index.
  - evidence_handoff(session): load saved task state.
  - evidence_log(run, start=1, end=80, stream="stderr", encoding="text", offset=0, length=65536): retrieve a redacted output range.
- telemetry: diagnostic hook receiver for explicitly installed compatible hooks; it is not a context filter or budget enforcer.

MCP does not intercept native Codex reads, shell output, hidden reasoning, or conversation history. Observation masking is not supported. The local byte budget is not a hard total-token limit. Codex subscription quota is not exposed by the installed interface.

## Providers, configuration, and privacy

- config [--set JSON]: inspect/update validated local settings, including profiles, observed task budget, and auxiliary mode.
- policy NAME [--set JSON]: project permission gate for external source context.
- secret, secret --stdin, secret --remove: check presence, set, or remove the TypeSafe credential without displaying it. Never put secrets in prompts, argv, logs, Git, or generated skill files.
- calibrate DATASET.json: calibrate auxiliary answer thresholds on explicitly labeled calibration data, not final evaluation data.
- Jev is optional; without configured credential, enabled auxiliary mode, explicit external permission, and sufficient candidates, local retrieval remains the fallback. A Jev result cannot approve a patch. Do not make paid requests unless specifically authorized.
- metrics: show recorded harness Codex usage and auxiliary events; cached input is a subset of input and reasoning output is a subset of output. Subscription quota is unavailable and must not be estimated from API prices.
- benchmark MANIFEST [--execute|--report]: execute/report isolated paired evaluations; preserve failures and all attempts. A retrieval experiment alone does not establish task-token savings.

## State maintenance

- backup DEST [--bundle], restore SOURCE, recover [--source SOURCE]: preserve/restore SQLite state and supported bundles. Check exact command help first; preserve recovery artifacts.
- export DEST: export indexed metadata and logs; it may contain project source or sensitive text and must remain private.
- prune [--days N]: delete eligible historical runs/events and expired caches according to retention rules.
- --home PATH: select an alternate state root before the command, useful for isolated validation.

## Safe operating defaults

- Re-index after edits, branch/worktree changes, or a stale status; never use stale evidence silently.
- Keep search, graph depth, output lines, and context bytes bounded. Read source only when needed.
- Do not send code externally or enable paid providers unless the user explicitly asks. Do not dump environment variables, auth stores, or secret files.
- Keep the project's established test/build commands and run only those needed for acceptance.
- Use ce COMMAND --help before relying on rarely used flags; this catalog cannot override the installed CLI's contracts.
