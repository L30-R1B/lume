"""Real labeled calibration and separate holdout for direct-definition evidence ranking."""

import json
import os
from pathlib import Path
from codex_economy.store import Store
from codex_economy.providers import Jev, calibrate

base = Path(__file__).resolve().parents[1]
os.environ["CE_JEV_MODEL"] = "jev-1.14.0"
calibration = []
holdout = []
runs = []
with Store() as store:
    for split, names in [
        (
            "calibration",
            [
                "add",
                "subtract",
                "multiply",
                "divide",
                "square",
                "cube",
                "clamp",
                "distance",
                "minimum",
                "maximum",
                "normalize",
                "validate",
            ],
        ),
        ("holdout", ["connect", "decode", "encode", "sanitize"]),
    ]:
        cases = []
        for name in names:
            cases.extend(
                [
                    {
                        "task": "Find the definition of " + name,
                        "candidate": f"def {name}(value):\n    return value\n",
                        "label": 1,
                    },
                    {
                        "task": "Find the definition of " + name,
                        "candidate": f"# Documentation mentions {name}; no implementation is provided.\n",
                        "label": 0,
                    },
                ]
            )
        for offset in range(0, len(cases), 12):
            batch = cases[offset : offset + 12]
            state = {
                "split": split,
                "cases": [{"id": i, "task": c["task"], "candidate": c["candidate"]} for i, c in enumerate(batch)],
            }
            questions = {
                str(i): {
                    "type": "noul",
                    "instructions": f"Does candidate {i} actually define the function requested by its task, rather than merely mention it?",
                }
                for i in range(len(batch))
            }
            result = Jev(store).ask(state, questions, allowed=True)
            runs.append(result)
            if result["mode"] not in ("jev", "jev-cache"):
                raise RuntimeError("Real Jev calibration failed: " + str(result.get("error")))
            for i, case in enumerate(batch):
                row = {"split": split, "probability": result["answers"][str(i)]["noul"], "label": case["label"]}
                (calibration if split == "calibration" else holdout).append(row)
    threshold = calibrate(calibration)
    evaluated = [int(r["probability"] >= threshold["threshold"]) == r["label"] for r in holdout]
    report = {
        "model": "jev-1.14.0",
        "question_domain": "actual named function definition vs mention; not general correctness",
        "calibration": threshold,
        "holdout": {"n": len(holdout), "correct": sum(evaluated), "accuracy": sum(evaluated) / len(evaluated)},
        "calibration_rows": calibration,
        "holdout_rows": holdout,
        "runs": runs,
        "acceptance_decision": False,
        "universal_threshold_claimed": False,
    }
    (base / "evidence/jev-real-calibration.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "calibration_n": len(calibration),
                "holdout_n": len(holdout),
                "holdout_accuracy": report["holdout"]["accuracy"],
                "threshold": threshold["threshold"],
                "requests": sum(r["requests"] for r in runs),
            }
        )
    )
