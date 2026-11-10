# Evidence archive

This directory keeps the collected evaluation data and validation records used by the project reports. The current benchmark verdict is based only on the post-fix A/E confirmation; earlier pilots, partial runs, failed attempts, and other evaluations remain separate.

## Metric entry points

- `metrics-preview.json`: machine-readable aggregates, all experiment summaries, provider usage, and linked validation artifacts.
- `metrics-preview.md`: human-readable overview and interpretation warnings.
- `metrics-preview-tasks.csv`: one row per recorded experiment attempt, including acceptance, usage availability, token fields, elapsed time, and action counts.
- `runtime-metrics-summary.json` and `runtime-runs.csv`: anonymized historical CLI telemetry, kept separate because overlap with experiment data cannot be excluded.
- `representative-confirmation-v3/`: current frozen confirmation, including per-attempt results and raw Codex event/verification artifacts for synthetic fixtures.

Historical experiment directories are intentionally preserved. Their status is explained in `docs/benchmark.md`; a complete or successful queue does not by itself imply equivalent quality or a current verdict.

## Rebuild the aggregates

From the repository root:

```bash
python3 scripts/metrics_preview.py
```

The script reads only versioned result files in this repository. It removes local host names and personal absolute paths from the aggregate view, retains measured counters, and does not add potentially overlapping historical runtime usage to experiment totals.

Raw event files document synthetic evaluation tasks. They can include local execution paths from the original run, but contain no authentication store or credential file. Project state databases, Codex homes, and benchmark workspaces are excluded from version control.
