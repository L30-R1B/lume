"""Isolated faithful selection variants inspired by pruning/chunk-localization research."""

import json
import time
from .engine import Engine

METHODS = {
    "faithful": {"mode": "lexical", "principle": "exact lexical snippets"},
    "ast-prune": {
        "mode": "ast-prune",
        "principle": "whole AST symbol spans plus typed graph neighbors; no token deletion",
    },
    "longcodezip": {
        "mode": "longcodezip",
        "principle": "coarse file ranking then fine source spans with budget and stop limits",
    },
    "hierarchical": {
        "mode": "hierarchical",
        "principle": "file ranking plus declared topic documents and graph refines",
    },
}


def compare(store, project, query, budget=6000):
    results = {}
    for name, config in METHODS.items():
        started = time.monotonic()
        packet = Engine(store).context(project, query, budget, config["mode"])
        results[name] = {
            "seconds": time.monotonic() - started,
            "serialized_bytes": len(json.dumps(packet).encode()),
            "source_bytes": sum(len(e["source"].encode()) for e in packet["evidence"]),
            "evidence": packet,
            "principle": config["principle"],
            "paper_equivalence": False,
        }
    return {
        "results": results,
        "codex_task_token_savings": None,
        "comparison_scope": "retrieval only; run paired Codex benchmark to measure task economy",
        "llmlingua": {
            "status": "optional_external_model_not_installed",
            "reason": "neural token deletion is not applied to source; faithful selection remains default",
        },
        "closed_model_internal_pruning": "not applicable without internal representations",
    }


def neural(store, project, path, rate=0.5):
    import os
    import subprocess
    from pathlib import Path

    root = Path.home() / ".local/share/codex-economy/experimental"
    python = Path(os.environ.get("CE_NEURAL_PYTHON", root / "llmlingua/bin/python"))
    model = Path(
        os.environ.get("CE_NEURAL_MODEL", root / "models/llmlingua-2-bert-base-multilingual-cased-meetingbank")
    )
    if not python.is_file() or not model.is_dir():
        raise ValueError("Optional LLMLingua environment/model unavailable; install with scripts/install_neural.py")
    if Path(path).suffix.lower() not in (".md", ".txt", ".rst"):
        raise ValueError("Neural compression experiment accepts documents only; source remains exact")
    original = Engine(store).read(project, path, 1, 200)
    if len(original["source"]) > 16000:
        raise ValueError("Document excerpt exceeds neural experiment limit")
    process = subprocess.run(
        [str(python), "-m", "codex_economy.neural_worker"],
        input=json.dumps({"text": original["source"], "model": str(model), "rate": rate}),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={
            **os.environ,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        },
    )
    if process.returncode:
        raise ValueError("Neural worker failed: " + process.stderr[-1500:])
    result = json.loads(process.stdout)
    result["original_evidence"] = original
    result["usage_scope"] = "document experiment only; not Codex task savings"
    store.event("neural", result)
    return result
