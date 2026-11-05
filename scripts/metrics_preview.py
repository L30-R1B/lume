"""Snapshot every collected experiment metric without merging duplicate event artifacts."""

import csv
import datetime
import json
import statistics
from pathlib import Path

base = Path(__file__).resolve().parents[1]
original = base.parent / "codex-economy"
experiments = []
task_rows = []
for root, names in [
    (original, ["benchmark", "confirmation", "confirmation-v2"]),
    (base, ["editor-pilot", "editor-confirmation", "editor-confirmation-r2"]),
]:
    for name in names:
        source = root / "evidence" / name / "results.jsonl"
        if not source.exists():
            continue
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
            known = bool(row.get("usage")) or row.get("run") is None
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
        experiments.append({"experiment": name, "records": len(rows), "source": str(source), "groups": groups})
artifacts = {}
for name in [
    "performance.json",
    "performance-v2.json",
    "performance-final.json",
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
]:
    path = base / "evidence" / name
    if not path.exists():
        path = original / "evidence" / name
    if path.exists():
        value = json.loads(path.read_text())
        if name == "app-server-real.json":
            value.pop("events", None)
        if name in ("performance.json", "performance-v2.json"):
            for metric in ("cold_seconds", "incremental_seconds", "lexical_seconds"):
                value[metric].pop("samples", None)
        artifacts[name] = value
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
summary = {
    "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "experiments": experiments,
    "artifacts": artifacts,
    "overall_observed_experiment_tokens": sum(row["total_tokens"] for row in task_rows),
    "overall_experiment_attempts": len(task_rows),
    "overall_accepted": sum(row["accepted"] for row in task_rows),
    "overall_unavailable_usage": sum(not row["usage_available"] for row in task_rows),
    "latest_codex_profile_smoke_usage_separate_from_experiments": smoke_usage,
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
    "warnings": [
        "historical exploratory rounds are not confirmation",
        "one native B run has incomplete usage after subscription limit",
        "latest editor confirmation used code before subsequent hardening",
        "neural document compression is not Codex task savings",
        "cached input is part of input, reasoning output part of output",
        "experiment totals exclude other Codex validation calls; inspect their individual event logs",
    ],
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
