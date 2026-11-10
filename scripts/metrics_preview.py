"""Snapshot every collected experiment metric without merging duplicate event artifacts."""

import csv
import datetime
import json
import re
import statistics
from pathlib import Path

base = Path(__file__).resolve().parents[1]
experiments = []
task_rows = []
experiment_names = [
    "benchmark",
    "confirmation",
    "confirmation-v2",
    "editor-pilot",
    "editor-confirmation",
    "editor-confirmation-r2",
    "representative-pilot",
    "representative-confirmation",
    "representative-confirmation-v2",
    "representative-confirmation-redaction-remediation",
    "representative-confirmation-v3",
]
for name in experiment_names:
    source = base / "evidence" / name / "results.jsonl"
    if not source.is_file():
        raise FileNotFoundError(f"Required collected metrics are missing: {source.relative_to(base)}")
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    groups = {}
    for row in rows:
        arm = row["arm"]
        g = groups.setdefault(
            arm,
            {
                "attempts": 0,
                "accepted": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "reasoning_output_tokens": 0,
                "usage_unavailable_attempts": 0,
                "seconds": 0,
                "index_seconds": 0,
                "actions": 0,
                "times": [],
            },
        )
        g["attempts"] += 1
        g["accepted"] += int(row["accepted"])
        g["seconds"] += row.get("seconds", 0)
        g["index_seconds"] += row.get("index_seconds", 0)
        g["actions"] += row.get("actions") or 0
        g["times"].append(row.get("seconds", 0))
        invocations = row.get(
            "codex_invocations", 0 if row.get("all_model_attempts") == [] and row.get("run") is None else 1
        )
        known = bool(row.get("usage")) or invocations == 0
        if not known:
            g["usage_unavailable_attempts"] += 1
        tokens = {
            key: sum(u.get(key, 0) for u in row.get("usage", []))
            for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
        }
        for key, value in tokens.items():
            g[key] += value
        task_rows.append(
            {
                "experiment": name,
                "task": row["task"],
                "family": row["family"],
                "repeat": row["repeat"],
                "arm": arm,
                "accepted": row["accepted"],
                "usage_available": known,
                "seconds": row.get("seconds", 0),
                "index_seconds": row.get("index_seconds", 0),
                "actions": row.get("actions"),
                **tokens,
                "total_tokens": tokens["input_tokens"] + tokens["output_tokens"],
                "run": row.get("run"),
            }
        )
    for group in groups.values():
        times = sorted(group.pop("times"))
        group["total_tokens"] = group["input_tokens"] + group["output_tokens"]
        group["tokens_per_accepted"] = (
            group["total_tokens"] / group["accepted"]
            if group["accepted"] and not group["usage_unavailable_attempts"]
            else None
        )
        group["cache_fraction"] = (
            group["cached_input_tokens"] / group["input_tokens"] if group["input_tokens"] else None
        )
        group["p50_seconds"] = statistics.median(times)
        group["p95_seconds"] = times[min(len(times) - 1, int(len(times) * 0.95))]
    experiments.append(
        {"experiment": name, "records": len(rows), "source": source.relative_to(base).as_posix(), "groups": groups}
    )


def public_safe(value, key=None):
    """Preserve useful measurements while removing machine-specific identity and local paths."""
    if isinstance(value, dict):
        if key == "environment_before":
            memory = {}
            for line in value.get("meminfo", "").splitlines():
                name, separator, measurement = line.partition(":")
                if separator and name in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                    memory[name] = measurement.strip()
            load = value.get("loadavg", "").split()
            result = {"load_average_1_5_15_minutes": " ".join(load[:3])} if load else {}
            if memory:
                result["memory_summary"] = memory
            return result
        return {k: public_safe(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [public_safe(item, key) for item in value]
    if isinstance(value, str):
        if key in ("node", "hostname"):
            return "local host name omitted"
        if key in ("loadavg", "environment_after_loadavg"):
            return " ".join(value.split()[:3])
        return re.sub(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^\s,\"']+", "<local-path>", value)
    return value
artifacts = {}
for name in [
    "performance.json",
    "performance-v2.json",
    "performance-final.json",
    "performance-final-1.json",
    "performance-final-2.json",
    "performance-final-3.json",
    "neural-offline-enforced.json",
    "jev-live-integration.json",
    "jev-real-calibration.json",
    "jev-ranking-real.json",
    "framework-validation.json",
    "android-validation.json",
    "app-server-real.json",
    "hooks-real-events.json",
    "release-validation.json",
    "installed-source-match-v2.json",
    "delegation-live.json",
    "hooks-project-latest.json",
    "release-schema3.json",
    "installed-source-match-schema3.json",
    "dependency-audit-final.json",
    "representative-pilot/report.json",
    "representative-confirmation/report.json",
    "representative-confirmation-v2/report.json",
    "representative-confirmation-v2/environment.json",
    "representative-confirmation-v2/execution-home.json",
    "representative-confirmation-redaction-remediation/report.json",
    "representative-confirmation-v3/report.json",
    "representative-confirmation-v3/environment.json",
    "android-emulator-runtime.json",
]:
    path = base / "evidence" / name
    if path.exists():
        value = json.loads(path.read_text())
        if name == "app-server-real.json":
            value.pop("events", None)
        if name in ("performance.json", "performance-v2.json"):
            for metric in ("cold_seconds", "incremental_seconds", "lexical_seconds"):
                value[metric].pop("samples", None)
        artifacts[name] = public_safe(value)
jev_runs = []
if "jev-live-integration.json" in artifacts:
    jev_runs.append(artifacts["jev-live-integration.json"])
if "jev-real-calibration.json" in artifacts:
    jev_runs += artifacts["jev-real-calibration.json"]["runs"]
if "jev-ranking-real.json" in artifacts:
    jev_runs += artifacts["jev-ranking-real.json"]["real_calls"]
profile_smoke = base / "evidence/codex-profile-mcp-latest.jsonl"
smoke_usage = None
if profile_smoke.exists():
    for line in profile_smoke.read_text().splitlines():
        event = json.loads(line)
        if event.get("type") == "turn.completed":
            smoke_usage = event.get("usage")
warnings = [
    "historical exploratory rounds are not confirmation",
    "representative-confirmation is an earlier 24/72 partial round after its frozen Codex configuration changed",
    "representative-confirmation-v2 measured the redaction bug before its fix and remains preserved as a separate result",
    "the redaction-remediation follow-up is one targeted task and is not part of the overall confirmation",
    "Jev arm D was not run because paid auxiliary calls are disabled",
    "the supported account subscription usage counter is unavailable",
    "the anonymized historical runtime snapshot is separate and is not added to experiment totals because overlap cannot be excluded",
    "four historical attempts have unknown usage; one native B run hit the subscription limit",
    "historical editor confirmation used code before subsequent hardening",
    "neural document compression is not Codex task savings",
    "cached input is part of input, reasoning output part of output",
    "experiment totals exclude other Codex validation calls; inspect their individual event logs",
]
current_report = artifacts.get("representative-confirmation-v3/report.json")
runtime_metrics = json.loads((base / "evidence/runtime-metrics-summary.json").read_text())
if current_report:
    low, high = current_report["reduction_bootstrap_95_percent"] or (None, None)
    interval_text = (
        f"95% task-cluster interval {low:.2%}–{high:.2%}"
        if low is not None
        else "95% task-cluster interval unavailable"
    )
    quality = current_report["paired_quality"]
    warnings.append(
        "current A/E confirmation: "
        f"{current_report['observed_reduction_fraction']:.2%} observed reduction, {interval_text}; "
        f"paired acceptance A-only={quality['baseline_only']}, E-only={quality['comparison_only']}; "
        f"verdict={current_report['goal_80_percent']}"
    )
summary = {
    "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "experiments": experiments,
    "artifacts": artifacts,
    "overall_observed_experiment_tokens": sum(row["total_tokens"] for row in task_rows),
    "overall_experiment_attempts": len(task_rows),
    "overall_accepted": sum(row["accepted"] for row in task_rows),
    "overall_unavailable_usage": sum(not row["usage_available"] for row in task_rows),
    "latest_codex_profile_smoke_usage_separate_from_experiments": smoke_usage,
    "historical_runtime_metrics_separate_from_experiments": runtime_metrics,
    "current_confirmation_verdict": artifacts.get("representative-confirmation-v3/report.json"),
    "jev_real": {
        "requests": sum(r["requests"] for r in jev_runs),
        "input_tokens": sum(r.get("usage", {}).get("input_tokens", 0) for r in jev_runs),
        "output_tokens": sum(r.get("usage", {}).get("output_tokens", 0) for r in jev_runs),
        "latency_seconds": [r["latency_seconds"] for r in jev_runs],
        "monetary_cost": None,
    },
    "unavailable": [
        "supported subscription quota counter",
        "monetary auxiliary billing",
        "fully classified rereads and compactions for every historical run",
    ],
    "warnings": warnings,
}
(base / "evidence/metrics-preview.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
with (base / "evidence/metrics-preview-tasks.csv").open("w") as file:
    writer = csv.DictWriter(file, fieldnames=list(task_rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(task_rows)
lines = [
    "# Prévia das métricas coletadas",
    summary["captured_utc"],
    "",
    "Tokens totais = entrada + saída; cache é subconjunto de entrada; raciocínio é subconjunto de saída. Rodadas não são somadas como percentuais de economia.",
    "",
    "Veredito A/E atual: "
    + (
        f"{current_report['goal_80_percent']} ({current_report['observed_reduction_fraction']:.2%} observada; "
        f"IC 95% agrupado por tarefa {current_report['reduction_bootstrap_95_percent'][0]:.2%}–"
        f"{current_report['reduction_bootstrap_95_percent'][1]:.2%}; aceite A/E "
        f"{current_report['groups']['A']['accepted']}/{current_report['groups']['E']['accepted']})."
        if current_report and current_report["reduction_bootstrap_95_percent"]
        else "inconclusivo (confirmação ausente ou incompleta)."
    ),
    "",
    "| Rodada | Braço | Tentativas | Aceitas | Entrada | Cache | Saída | Raciocínio | Total observado | Tokens/aceita | Tempo s | p50 s | p95 s | Ações |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for experiment in experiments:
    for arm, g in experiment["groups"].items():
        lines.append(
            "|"
            + "|".join(
                map(
                    str,
                    [
                        experiment["experiment"],
                        arm,
                        g["attempts"],
                        g["accepted"],
                        g["input_tokens"],
                        g["cached_input_tokens"],
                        g["output_tokens"],
                        g["reasoning_output_tokens"],
                        g["total_tokens"],
                        g["tokens_per_accepted"],
                        round(g["seconds"], 3),
                        round(g["p50_seconds"], 3),
                        round(g["p95_seconds"], 3),
                        g["actions"],
                    ],
                )
            )
            + "|"
        )
lines += [
    "",
    "Snapshot histórico do CLI, fora do total experimental: "
    + f"{runtime_metrics['recorded_runs']} execuções, {runtime_metrics['codex_observed_turns']} turnos Codex observados, "
    + f"{runtime_metrics['codex_total_tokens']:,} tokens. Não some este snapshot aos experimentos: possível sobreposição não pôde ser excluída.",
    "Métricas anonimizadas por execução: runtime-runs.csv. IDs, projetos, comandos, prompts e saídas foram omitidos.",
    "",
    "Detalhe por tarefa: metrics-preview-tasks.csv. Artefatos e todas as categorias adicionais: metrics-preview.json.",
    "",
    json.dumps(summary["jev_real"], indent=2),
    "",
    "Alertas:",
] + ["- " + w for w in summary["warnings"]]
(base / "evidence/metrics-preview.md").write_text("\n".join(lines))
print(
    json.dumps(
        {
            "captured_utc": summary["captured_utc"],
            "attempts": len(task_rows),
            "accepted": summary["overall_accepted"],
            "observed_tokens": summary["overall_observed_experiment_tokens"],
            "jev_real": summary["jev_real"],
        }
    )
)
